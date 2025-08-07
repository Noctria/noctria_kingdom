"""
💼 OrderExecution（Fintokei対応リファクタ版）
- MT5注文APIへの注文リクエスト送信
- 取引リスクは「最大0.5～1%」ガード
- 必ず「損切(SL)」指定必須（TPは任意）
- ロット自動計算（許容リスクに収まるLotのみ執行）
- バリデーション違反時は注文不可＆理由返却
"""

import requests
import math

class OrderExecution:
    def __init__(
        self,
        api_url="http://host.docker.internal:5001/order",
        max_risk_per_trade=0.01,   # 最大1%まで（既定値: 1% = 0.01）
        min_risk_per_trade=0.005,  # 最小0.5%（既定値: 0.5% = 0.005）
        get_balance_api_url=None,  # 残高取得API（任意：自前実装 or 埋め込み想定）
        symbol_default_pip=0.01,   # USDJPY等: 0.01
    ):
        self.api_url = api_url
        self.max_risk = max_risk_per_trade
        self.min_risk = min_risk_per_trade
        self.get_balance_api_url = get_balance_api_url  # API叩く設計も許容
        self.symbol_default_pip = symbol_default_pip

    def get_account_balance(self):
        """
        口座残高を取得（API経由 or 手動設定用ダミー）
        ※本番はAPIでMT5から取得推奨。ここでは固定値サンプル。
        """
        # 例: 別APIにGETして取得する場合
        if self.get_balance_api_url:
            try:
                r = requests.get(self.get_balance_api_url, timeout=5)
                r.raise_for_status()
                return float(r.json().get("balance", 0))
            except Exception as e:
                print(f"口座残高取得失敗: {e}")
                return None
        # 仮: ダミー残高
        return 10000.0

    def calc_lot_size(
        self,
        balance,
        entry_price,
        stop_loss,
        risk_percent=None,
        symbol="USDJPY",
        contract_size=100000,  # FX 1Lot=10万通貨（証券会社による）
    ):
        """
        損切ラインに基づき、最大リスク0.5～1%内となるLot数を自動算出
        """
        risk_percent = risk_percent or self.max_risk
        risk_amount = balance * risk_percent

        # 価格差：SLがどちら向きか自動判定
        price_diff = abs(entry_price - stop_loss)
        if price_diff < self.symbol_default_pip:
            return 0, "エントリー価格と損切(SL)が近すぎます"

        # 1pipあたりの損益＝コントラクトサイズ・通貨ペアによる
        # USDJPY例: 1Lot=10万通貨→1pip=1000円（0.01円=1pip）
        pip_value = contract_size * self.symbol_default_pip
        # 損切到達時の総損失額＝（1pip値幅 × 価格差[pip]） × lot数
        pip_diff = price_diff / self.symbol_default_pip
        loss_per_lot = pip_value * pip_diff
        if loss_per_lot == 0:
            return 0, "SL値幅が不正です"
        # ロット数（最大リスク額内に収まるように）
        lot = risk_amount / loss_per_lot

        # 通貨会社・サーバーの最小ロット単位に切り上げ（例: 0.01、0.1 Lot）
        min_lot = 0.01
        lot = max(min_lot, math.floor(lot * 100) / 100)
        return lot, None

    def validate_order(
        self,
        balance,
        entry_price,
        stop_loss,
        risk_percent=None,
    ):
        """
        事前バリデーション
        - SL必須/指定済み
        - リスク比率が最小/最大範囲内
        - ロットサイズが許容範囲内
        """
        # 1. 損切(SL)必須
        if stop_loss is None or stop_loss == 0:
            return False, "損切(SL)は必須です"
        # 2. SL幅が近すぎ/遠すぎNG
        price_diff = abs(entry_price - stop_loss)
        if price_diff < self.symbol_default_pip:
            return False, "エントリーとSLの幅が狭すぎます"
        # 3. ロット自動計算
        lot, err = self.calc_lot_size(
            balance, entry_price, stop_loss, risk_percent
        )
        if err:
            return False, err
        # 4. 許容ロット範囲チェック（サンプル: 100Lot以下のみ許容）
        if not (0.01 <= lot <= 100.0):
            return False, f"ロット数が異常です: {lot:.2f}"
        # 5. リスク％範囲
        percent = (abs(entry_price - stop_loss) * lot * 100000) / balance
        if percent > self.max_risk * 1.02:  # 許容上限を1.02倍まで
            return False, f"この損切幅だとリスクが上限({self.max_risk*100:.2f}%)を超えます"
        if percent < self.min_risk * 0.98:  # 許容下限を0.98倍まで
            return False, f"この損切幅だとリスクが下限({self.min_risk*100:.2f}%)未満です"
        return True, lot

    def execute_order(
        self,
        symbol,
        entry_price,
        stop_loss,
        order_type="buy",
        take_profit=None,
        risk_percent=None,
        magic_number=None,
        comment=None,
    ):
        """
        ✅ 注文リクエスト（リスク＆SL必須・ロット自動計算・バリデーション付）
        - symbol: 通貨ペア (例: "USDJPY")
        - entry_price: エントリー予定価格
        - stop_loss: 必須（価格 or pips絶対値）
        - take_profit: 任意（AI推奨/なし可）
        - risk_percent: 任意（最大1%、デフォルトはmax_risk）
        """
        # 口座残高を取得
        balance = self.get_account_balance()
        if not balance:
            return {"status": "error", "message": "口座残高取得エラー"}
        # 事前バリデーション
        valid, lot_or_msg = self.validate_order(
            balance, entry_price, stop_loss, risk_percent
        )
        if not valid:
            return {"status": "error", "message": lot_or_msg}
        lot = lot_or_msg

        payload = {
            "symbol": symbol,
            "lot": lot,
            "type": order_type,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "magic_number": magic_number,
            "comment": comment,
        }
        # 実際の発注
        try:
            response = requests.post(self.api_url, json=payload, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": str(e)}

# ==========================
# テスト用サンプル
# ==========================
if __name__ == "__main__":
    executor = OrderExecution()
    # テスト: 口座10000ドル、USDJPY 1Lot=10万通貨
    # エントリー: 155.00円、損切: 154.50円（=50pips幅、典型的なトレード例）
    result = executor.execute_order(
        symbol="USDJPY",
        entry_price=155.00,
        stop_loss=154.50,
        order_type="buy",
        take_profit=155.80,
        comment="Fintokeiテスト（SL必須/リスク管理）"
    )
    print("MT5注文結果:", result)
