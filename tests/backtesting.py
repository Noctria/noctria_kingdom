import pandas as pd
import numpy as np

class Backtesting:
    """過去データを用いて戦略のパフォーマンスを検証"""

    def __init__(self, historical_data):
        self.data = historical_data

    def run_backtest(self):
        """シンプルな移動平均戦略のテスト"""
        self.data["SMA_50"] = self.data["price"].rolling(window=50).mean()
        self.data["SMA_200"] = self.data["price"].rolling(window=200).mean()

        self.data["signal"] = np.where(self.data["SMA_50"] > self.data["SMA_200"], 1, -1)
        return self.data[["date", "price", "signal"]]

# ✅ バックテスト適用テスト
if __name__ == "__main__":
    mock_data = pd.DataFrame({
        "date": pd.date_range(start="2023-01-01", periods=300),
        "price": np.random.uniform(1.2, 1.5, 300)
    })
    backtester = Backtesting(mock_data)
    results = backtester.run_backtest()

    print("Backtesting Results:\n", results.head())
