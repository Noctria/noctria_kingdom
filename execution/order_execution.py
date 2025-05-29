import MetaTrader5 as mt5

class OrderExecution:
    """Pythonから直接MT5 APIを呼び、注文を実行"""

    def __init__(self, symbol="EURUSD", max_spread=2.0, min_liquidity=100):
        self.symbol = symbol
        self.max_spread = max_spread
        self.min_liquidity = min_liquidity

    def execute_trade(self, order_type, lot_size):
        """MetaTrader5 APIを使い、直接注文を送信"""
        if not mt5.initialize():
            return "MT5接続失敗"

        # 現在のBid価格取得
        symbol_info = mt5.symbol_info_tick(self.symbol)
        spread = symbol_info.ask - symbol_info.bid
        liquidity = mt5.symbol_info(self.symbol).volume

        # 取引回避条件
        if spread > self.max_spread or liquidity < self.min_liquidity:
            return f"⚠️ Trade avoided: Spread={spread:.2f}, Liquidity={liquidity}"

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": lot_size,
            "type": mt5.ORDER_TYPE_BUY if order_type == "BUY" else mt5.ORDER_TYPE_SELL,
            "price": symbol_info.bid,
            "magic": 123456,
            "comment": "Noctria Kingdom Trade"
        }
        
        result = mt5.order_send(request)
        mt5.shutdown()  # 接続を閉じる

        return result.comment if result.retcode == mt5.TRADE_RETCODE_DONE else f"Trade failed: {result.comment}"

# ✅ 注文テスト
if __name__ == "__main__":
    executor = OrderExecution()
    trade_result = executor.execute_trade("BUY", 0.1)
    print("Trade Execution Result:", trade_result)
