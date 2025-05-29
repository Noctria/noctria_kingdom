import MetaTrader5 as mt5
import pandas as pd

class OrderExecution:
    """トレードのエントリー／エグジットを管理"""

    def __init__(self, symbol="EURUSD"):
        self.symbol = symbol

    def execute_trade(self, order_type, lot_size):
        """注文シグナルをCSVに保存（MQL5が読み取る）"""
        trade_data = {"symbol": self.symbol, "order_type": order_type, "lot_size": lot_size}
        df = pd.DataFrame([trade_data])
        df.to_csv("trade_signal.csv", index=False)
        return f"Trade signal saved: {order_type} {lot_size}"

# ✅ 注文シグナルのテスト
if __name__ == "__main__":
    executor = OrderExecution()
    result = executor.execute_trade("BUY", 0.1)
    print(result)
