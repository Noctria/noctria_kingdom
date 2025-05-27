import numpy as np

class AdaptiveTrading:
    """市場環境の変化に対応する自律型トレーディング戦略"""
    
    def __init__(self, adaptation_threshold=0.05):
        self.adaptation_threshold = adaptation_threshold  # 戦略変更の閾値
    
    def process(self, market_data):
        """市場データを分析し、適応戦略を決定"""
        volatility = self._calculate_volatility(market_data["price_history"])
        if volatility > self.adaptation_threshold:
            return "SHIFT_STRATEGY"
        return "MAINTAIN_STRATEGY"

    def _calculate_volatility(self, price_history):
        """市場の変動率を計算"""
        return np.std(price_history) / np.mean(price_history)

# ✅ 自己適応戦略テスト
if __name__ == "__main__":
    trader = AdaptiveTrading()
    mock_market_data = {"price_history": [1.2050, 1.2100, 1.2150, 1.2075, 1.2125]}
    strategy_decision = trader.process(mock_market_data)
    print("Adaptive Trading Decision:", strategy_decision)
