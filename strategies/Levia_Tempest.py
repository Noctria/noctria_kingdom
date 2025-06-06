import numpy as np
from data.market_data_fetcher import MarketDataFetcher  # ✅ 修正: 正しいインポート
from core.risk_management import RiskManagement  # ✅ クラス名の修正

class LeviaTempest:
    """スキャルピング戦略を適用する高速トレードAI（改修版）"""

    def __init__(self, threshold=0.05, min_liquidity=120, max_spread=0.018):
        self.threshold = threshold  # 価格変動の閾値
        self.min_liquidity = min_liquidity  # 最低市場流動性（調整済み）
        self.max_spread = max_spread  # 最大スプレッド（調整済み）
        self.market_fetcher = MarketDataFetcher(api_key="YOUR_API_KEY")
        self.risk_manager = RiskManagement()  # ✅ クラス名を修正

    def process(self, market_data):
        """市場データを分析し、短期トレード戦略を決定"""
        price_change = self._calculate_price_change(market_data)
        liquidity = market_data["volume"]
        spread = market_data["spread"]
        order_block_impact = market_data["order_block"]
        volatility = market_data["volatility"]

        # 大口注文の影響を考慮
        adjusted_threshold = self.threshold * (1 + order_block_impact)

        # 流動性とスプレッドのチェック
        if liquidity < self.min_liquidity or spread > self.max_spread:
            return "HOLD"

        # スキャルピングロジック適用
        if price_change > adjusted_threshold and volatility < 0.2:
            return "BUY"
        elif price_change < -adjusted_threshold and volatility < 0.2:
            return "SELL"
        else:
            return "HOLD"

    def _calculate_price_change(self, market_data):
        """市場データから価格変動を計算"""
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
