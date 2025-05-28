import MetaTrader5 as mt5
import pandas as pd

class TradeMonitor:
    """リアルタイムで注文状況をモニタリングするモジュール"""

    def __init__(self):
        pass

    def get_open_positions(self):
        """現在のオープンポジションを取得"""
        positions = mt5.positions_get()
        if positions:
            df = pd.DataFrame(list(positions), columns=positions[0]._asdict().keys())
            return df
        else:
            return "No active positions"

    def get_trade_history(self, days=1):
        """過去のトレード履歴を取得"""
        history = mt5.history_deals_get(days_ago=days)
        if history:
            df = pd.DataFrame(list(history), columns=history[0]._asdict().keys())
            return df
        else:
            return "No recent trades"

# ✅ トレード監視テスト
if __name__ == "__main__":
    monitor = TradeMonitor()
    open_positions = monitor.get_open_positions()
    trade_history = monitor.get_trade_history()

    print("Open Positions:\n", open_positions)
    print("Trade History:\n", trade_history)
