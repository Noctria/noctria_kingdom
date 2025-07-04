import numpy as np
from data_loader import MarketDataFetcher
from core.risk_management import RiskManager  # 修正済み

class LeviaTempest:
    """スキャルピング戦略を適用する高速トレードAI（改修版）"""

    def __init__(self, threshold=0.05, min_liquidity=120, max_spread=0.018):
        self.threshold = threshold  # 価格変動の閾値
        self.min_liquidity = min_liquidity  # 最低市場流動性
        self.max_spread = max_spread  # 最大スプレッド
        self.market_fetcher = MarketDataFetcher(api_key="YOUR_API_KEY")
        self.risk_manager = RiskManager()

    def process(self, market_data):
        """市場データを分析し、短期トレード戦略を決定"""
        try:
            price_change = self._calculate_price_change(market_data)
            liquidity = market_data["volume"]
            spread = market_data["spread"]
            order_block_impact = market_data["order_block"]
            volatility = market_data["volatility"]
        except KeyError as e:
            print(f"[Levia] ⚠️ 入力データ欠損: {e}")
            return "HOLD"

        adjusted_threshold = self.threshold * (1 + order_block_impact)

        print(f"[Levia] 📊 price_change={price_change:.5f}, liquidity={liquidity}, spread={spread}, volatility={volatility}, threshold={adjusted_threshold:.5f}")

        if liquidity < self.min_liquidity or spread > self.max_spread:
            print("[Levia] ⚠️ 流動性不足またはスプレッド超過 → HOLD")
            return "HOLD"

        if self.risk_manager.detect_anomalies():
            print("[Levia] 🛡️ リスク検知 → HOLD")
            return "HOLD"

        if price_change > adjusted_threshold and volatility < 0.2:
            return "BUY"
        elif price_change < -adjusted_threshold and volatility < 0.2:
            return "SELL"
        else:
            return "HOLD"

    def _calculate_price_change(self, market_data):
        return market_data["price"] - market_data["previous_price"]

# ✅ 改修後のスキャルピング戦略テスト
if __name__ == "__main__":
    levia_ai = LeviaTempest()
    mock_market_data = {
        "price": 1.2050, "previous_price": 1.2040,
        "volume": 150, "spread": 0.012, "order_block": 0.4,
        "volatility": 0.15
    }
    decision = levia_ai.process(mock_market_data)
    print("Scalping Decision:", decision)
