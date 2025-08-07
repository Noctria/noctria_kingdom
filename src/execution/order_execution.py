"""
💼 OrderExecutionクラス（Fintokeiルール完全対応版）
- 1トレード最大リスク0.5-1%以内＋SL必須化
- ロット自動計算＋リスク超過ブロック
"""

import requests

class OrderExecution:
    def __init__(self, api_url="http://host.docker.internal:5001/order", risk_percent=0.01, min_lot=0.01, max_lot=100):
        """
        :param risk_percent: 1回のトレードで許容する最大リスク割合（例：0.01→1%）
        :param min_lot: ブローカー最小ロット（例：0.01）
        :param max_lot: ブローカー最大ロット（例：100.0）
        """
        self.api_url = api_url
        self.risk_percent = risk_percent
        self.min_lot = min_lot
        self.max_lot = max_lot

    def calc_lot_size(self, balance, entry_price, stop_loss_price, pip_value=1000):
        """
        許容リスクから最適ロット数を逆算
        :param balance: 口座残高
        :param entry_price: エントリー価格
        :param stop_loss_price: 損切ライン
        :param pip_value: 1ロットの1pipsあたり価値（USDJPYなら約1000円）
        """
        risk_amount = balance * self.risk_percent
        stop_pips = abs(entry_price - stop_loss_price)
        if stop_pips == 0:
            return 0.0  # エラー防止
        lot = risk_amount / (stop_pips * pip_value)
        lot = max(self.min_lot, min(round(lot, 2), self.max_lot))
        return lot

    def execute_order(self, symbol, balance, entry_price, stop_loss_price, order_type="buy", pip_value=1000):
        """
        Fintokeiルールを強制する注文I/F
        :param balance: 現口座資金
        :param entry_price: 発注価格
        :param stop_loss_price: 損切価格（必須）
        :param pip_value: 通貨ペアごとのpips価値（デフォルト1000円/ロット）
        """
        # 必須パラメータバリデーション
        if stop_loss_price is None:
            return {"status": "error", "message": "stop_loss_price（損切ライン）は必須です"}

        lot = self.calc_lot_size(balance, entry_price, stop_loss_price, pip_value)
        if lot <= 0.0:
            return {"status": "error", "message": "計算上ロットサイズが0または負になりました。SL/エントリー価格が正しいか確認してください"}

        # 許容最大リスクを超える場合は発注不可
        risk_per_trade = abs(entry_price - stop_loss_price) * lot * pip_value
        if risk_per_trade > balance * self.risk_percent:
            return {"status": "error", "message": f"注文リスク({risk_per_trade:.0f})が許容値({balance * self.risk_percent:.0f})を超えます。SL/ロット/価格設定を見直してください"}

        payload = {
            "symbol": symbol,
            "lot": lot,
            "type": order_type,
            "entry_price": entry_price,
            "stop_loss": stop_loss_price
        }
        try:
            response = requests.post(self.api_url, json=payload, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # テスト例
    executor = OrderExecution(api_url="http://192.168.11.30:5001/order", risk_percent=0.01)
    # 仮定: 残高2000000円, エントリー価格160, 損切159.6なら0.4円幅
    result = executor.execute_order(
        symbol="USDJPY",
        balance=2_000_000,
        entry_price=160.0,
        stop_loss_price=159.6,
        order_type="buy",
        pip_value=1000  # USDJPYなら1ロット=1000円/1円
    )
    print("MT5注文結果:", result)
