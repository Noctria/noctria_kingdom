import numpy as np

class LeviaTempest:
    """スキャルピング戦略を適用する高速トレードAI"""
    
    def __init__(self, threshold=0.05, min_liquidity=100, max_spread=0.02):
        self.threshold = threshold  # 価格変動の閾値
        self.min_liquidity = min_liquidity  # 最低市場流動性
        self.max_spread = max_spread  # 最大スプレッド

    def process(self, market_data):
        """市場データを分析し、短期トレード戦略を決定"""
        price_change = self._calculate_price_change(market_data)
        liquidity = market_data["volume"]
        spread = market_data["spread"]

        # 条件: 十分な流動性がある & スプレッドが許容範囲内
        if liquidity < self.min_liquidity or spread > self.max_spread:
            return "HOLD"

        # スキャルピングロジック適用
        if price_change > self.threshold:
            return "BUY"
        elif price_change < -self.threshold:
            return "SELL"
        else:
            return "HOLD"

    def _calculate_price_change(self, market_data):
        """市場データから価格変動を計算"""
        return market_data["price"] - market_data["previous_price"]

# ✅ スキャルピング戦略適用
if __name__ == "__main__":
    levia_ai = LeviaTempest()
    mock_market_data = {
        "price": 1.2050, "previous_price": 1.2040,
        "volume": 150, "spread": 0.01
    }
    decision = levia_ai.process(mock_market_data)
    print("Scalping Decision:", decision)
