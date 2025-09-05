"""
💼 OrderExecutionクラス (Fintokei/FTMO仕様)
Docker/Linux側から Windows上のMT5サーバー (order_api.py) に発注リクエストを送る
リスク管理: 取引ごとの損失リスク0.5%～1%厳守・SL必須・TP任意
"""

import requests

class OrderExecution:
    def __init__(self, api_url="http://host.docker.internal:5001/order", account_balance=None, max_risk_percent=1.0, min_risk_percent=0.5):
        """
        :param api_url: Windows側のMT5サーバーのエンドポイントURL
        :param account_balance: 現在の口座残高（円・ドル等）。必須
        :param max_risk_percent: 1回のトレードの最大リスク（％）
        :param min_risk_percent: 1回のトレードの最小リスク（％）
        """
        self.api_url = api_url
        self.account_balance = account_balance  # ※事前に取得必須
        self.max_risk_percent = max_risk_percent
        self.min_risk_percent = min_risk_percent

    def calc_lot_size(self, symbol, stop_loss_pips, risk_percent):
        """
        リスク％に収めるロットサイズを計算（通貨ペアごとに調整可。JPYクロスなら1pips=0.01円等で調整）
        ※ 例: USDJPY, 口座残高100万円, リスク1%, SL30pips → 最大損失1万円を30pipsで割ってlot算出
        """
        if self.account_balance is None:
            raise ValueError("account_balance（口座残高）は必須です。")

        # 1pipsあたりの損失額: 通貨ペアにより異なる
        # 簡易例: USDJPY, 1lot=10万通貨, 1pips=1000円, 100000JPY単位
        PIPS_VALUE = 1000  # 仮。必要に応じて通貨ペアごとに取得
        max_loss = self.account_balance * (risk_percent / 100)
        lot = max_loss / (abs(stop_loss_pips) * PIPS_VALUE)
        return round(lot, 2)  # 小数点2桁で丸める

    def execute_order(self, symbol, lot, order_type="buy", stop_loss=None, take_profit=None, risk_percent=None, comment=None):
        """
        安全な注文I/F (SL必須/TP任意/lotはリスク0.5%～1%のみ許可)
        :param symbol: 通貨ペア (例: "USDJPY")
        :param lot: 注文ロット数（SLリスクにより計算されたもののみ許可）
        :param order_type: "buy" or "sell"
        :param stop_loss: SL幅（pips単位 or 価格）必須
        :param take_profit: TP幅（任意、AI判断に委任可）
        :param risk_percent: 実際のリスク率（0.5～1%でバリデーション）
        :param comment: 任意コメント
        """
        # 必須バリデーション
        if stop_loss is None:
            return {"status": "error", "message": "SL（ストップロス）は必須です"}
        if lot <= 0:
            return {"status": "error", "message": "ロット数が不正です"}
        risk_percent = risk_percent or self._infer_risk_percent(lot, stop_loss)
        if not (self.min_risk_percent <= risk_percent <= self.max_risk_percent):
            return {"status": "error", "message": f"許容リスク外: {risk_percent:.2f}%。許可範囲={self.min_risk_percent}～{self.max_risk_percent}%"}
        if self.account_balance is None:
            return {"status": "error", "message": "口座残高情報が未設定です"}

        payload = {
            "symbol": symbol,
            "lot": lot,
            "type": order_type,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_percent": risk_percent,
            "comment": comment
        }
        try:
            response = requests.post(self.api_url, json=payload, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": str(e)}

    def _infer_risk_percent(self, lot, stop_loss_pips):
        """
        ロットとSL幅からリスク率を逆算（＝事後バリデーション用。PIPS_VALUEは仮）
        """
        if self.account_balance is None:
            return None
        PIPS_VALUE = 1000  # USDJPY, 1lot, 1pips換算例
        risk_amount = lot * abs(stop_loss_pips) * PIPS_VALUE
        return round(100 * risk_amount / self.account_balance, 2)

# テスト例（本番運用時は必ず外部でaccount_balance等を取得してセット）
if __name__ == "__main__":
    # 仮の残高100万円（JPY）
    account_balance = 1_000_000
    executor = OrderExecution(api_url="http://192.168.11.30:5001/order", account_balance=account_balance)
    symbol = "USDJPY"
    stop_loss_pips = 30  # 30pips
    risk_percent = 1.0
    lot = executor.calc_lot_size(symbol, stop_loss_pips, risk_percent)
    result = executor.execute_order(
        symbol=symbol,
        lot=lot,
        order_type="buy",
        stop_loss=stop_loss_pips,
        take_profit=None,
        risk_percent=risk_percent,
        comment="Noctria/AI test order"
    )
    print("MT5注文結果:", result)
