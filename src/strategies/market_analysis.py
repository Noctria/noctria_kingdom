import numpy as np
import pandas as pd

class MarketAnalysis:
    """市場データを解析し、トレンドと異常を検出するモジュール"""
    
    def __init__(self):
        self.trend_threshold = 0.02  # トレンドの判定閾値
    
    def detect_trends(self, price_series):
        """価格データからトレンドを検出"""
        moving_avg = price_series.rolling(window=5).mean()
        trend_signal = (price_series - moving_avg) / moving_avg
        return trend_signal > self.trend_threshold

    def detect_anomalies(self, price_series):
        """異常値を検出"""
        mean_price = np.mean(price_series)
        std_dev = np.std(price_series)
        anomalies = price_series[(price_series < mean_price - 2*std_dev) | (price_series > mean_price + 2*std_dev)]
        return anomalies

# ✅ 市場データ解析のテスト
if __name__ == "__main__":
    mock_prices = pd.Series(np.random.uniform(1.2, 1.5, 100))
    analyzer = MarketAnalysis()
    
    trends = analyzer.detect_trends(mock_prices)
    anomalies = analyzer.detect_anomalies(mock_prices)

    print("Trend Detection:", trends.tail())
    print("Anomalies Detected:", anomalies)
