import numpy as np
import pandas as pd

class AnomalyDetection:
    """市場データの異常を検出し、リスクを評価するモジュール"""
    
    def __init__(self, threshold=2.0):
        self.threshold = threshold  # 異常値検出の閾値
    
    def detect_anomalies(self, price_series):
        """市場データから異常を検出"""
        mean_price = np.mean(price_series)
        std_dev = np.std(price_series)
        anomalies = price_series[(price_series < mean_price - self.threshold * std_dev) | 
                                 (price_series > mean_price + self.threshold * std_dev)]
        return anomalies

# ✅ 異常検出テスト
if __name__ == "__main__":
    mock_prices = pd.Series(np.random.uniform(1.2, 1.5, 100))
    detector = AnomalyDetection()
    
    detected_anomalies = detector.detect_anomalies(mock_prices)

    print("Detected Anomalies:", detected_anomalies)
