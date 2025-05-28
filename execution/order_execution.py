import MetaTrader5 as mt5

class OrderExecution:
    """トレードのエントリー／エグジットを管理するモジュール"""

    def __init__(self, symbol="EURUSD"):
        self.symbol = symbol

    def execute_trade(self, order_type, lot_size):
        """注文の送信"""
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": lot_size,
            "type": order_type,
            "price": mt5.symbol_info_tick(self.symbol).bid,
            "magic": 123456,
            "comment": "Noctria Kingdom Trade"
        }
        result = mt5.order_send(request)
        return result.comment if result.retcode == mt5.TRADE_RETCODE_DONE else "Trade failed"

# ✅ 注文執行テスト
if __name__ == "__main__":
    executor = OrderExecution()
    trade_result = executor.execute_trade(mt5.ORDER_TYPE_BUY, 0.1)
    print("Trade Execution Result:", trade_result)
