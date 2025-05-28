import numpy as np
import pandas as pd

class MarketRegimeDetector:
    """市場の状態を分類し、最適な戦略を適用するモジュール"""
    
    def __init__(self):
        self.thresholds = {"bull": 0.02, "bear": -0.02}
    
    def classify_market(self, price_series):
        """価格の変動を分析し、市場状態を分類"""
        trend = (price_series.iloc[-1] - price_series.iloc[0]) / price_series.iloc[0]
        if trend > self.thresholds["bull"]:
            return "BULLISH"
        elif trend < self.thresholds["bear"]:
            return "BEARISH"
        else:
            return "NEUTRAL"

# ✅ 市場状態分類テスト
if __name__ == "__main__":
    mock_prices = pd.Series(np.random.uniform(1.2, 1.5, 100))
    detector = MarketRegimeDetector()
    market_state = detector.classify_market(mock_prices)
    print("Market Regime:", market_state)
