import numpy as np

class AutoAdjustment:
    """市場環境に応じて戦略を自動調整するモジュール"""
    
    def __init__(self, sensitivity=0.1):
        self.sensitivity = sensitivity  # 変化検出の閾値
    
    def adjust_strategy(self, market_data):
        """市場データを分析し、戦略を適応"""
        volatility = self._calculate_volatility(market_data["price_history"])
        if volatility > self.sensitivity:
            return "ADJUST_STRATEGY"
        return "MAINTAIN_STRATEGY"

    def _calculate_volatility(self, price_history):
        """市場の変動率を計算"""
        return np.std(price_history) / np.mean(price_history)

# ✅ 自動戦略調整テスト
if __name__ == "__main__":
    adjuster = AutoAdjustment()
    mock_market_data = {"price_history": [1.2000, 1.2050, 1.2100, 1.2025, 1.2075]}
    adjustment = adjuster.adjust_strategy(mock_market_data)
    print("Strategy Adjustment Decision:", adjustment)
