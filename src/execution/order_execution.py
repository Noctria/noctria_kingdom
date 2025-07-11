"""
💼 OrderExecutionクラス
Docker/Linux側から Windows上のMT5サーバー (order_api.py) に発注リクエストを送る
"""

import requests

class OrderExecution:
    def __init__(self, api_url="http://host.docker.internal:5001/order"):
        """
        ✅ Windows側のMT5サーバーのエンドポイントURLを指定
        （Docker環境なら host.docker.internal でWindows側に接続可能）
        """
        self.api_url = api_url

    def execute_order(self, symbol, lot, order_type="buy"):
        """
        ✅ 注文リクエストを送信
        :param symbol: 通貨ペア (例: "USDJPY")
        :param lot: 注文ロット数 (例: 0.1)
        :param order_type: "buy" or "sell"
        :return: Windows側APIの応答(JSON)
        """
        payload = {
            "symbol": symbol,
            "lot": lot,
            "type": order_type
        }
        try:
            response = requests.post(self.api_url, json=payload, timeout=5)
            response.raise_for_status()  # HTTPステータスコードでエラー検知
            return response.json()
        except requests.exceptions.RequestException as e:
            # 例外があれば詳細を返す（テスト・開発向け）
            return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    executor = OrderExecution(api_url="http://192.168.11.30:5001/order")
    result = executor.execute_order("USDJPY", 0.1, order_type="buy")
    print("MT5注文結果:", result)
