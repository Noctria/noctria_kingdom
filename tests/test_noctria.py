import unittest
import numpy as np
from core.Noctria import Noctria
from data.data_loader import MarketDataFetcher

class TestNoctria(unittest.TestCase):
    """Noctria AIの統合戦略をバックテストする"""

    def setUp(self):
        """テスト開始前のセットアップ"""
        self.noctria = Noctria()
        self.market_fetcher = MarketDataFetcher(api_key="YOUR_API_KEY")

    def test_strategy_execution(self):
        """市場データを適用し、戦略精度を評価"""
        mock_market_data = {
            "price": 1.245, "volume": 1500, "sentiment": 0.75, "trend_strength": 0.6,
            "volatility": 0.18, "order_block": 0.5, "institutional_flow": 0.85,
            "short_interest": 0.55, "momentum": 0.92, "trend_prediction": "bullish",
            "liquidity_ratio": 1.3
        }
        trade_decision = self.noctria.execute_trade()
        print("Trade Decision:", trade_decision)

        self.assertIn(trade_decision, ["BUY", "SELL", "HOLD"])

    def test_market_analysis(self):
        """市場データの分析が正しく動作するかを確認"""
        market_data, risk_evaluation, optimal_strategy = self.noctria.analyze_market()
        self.assertIsNotNone(market_data)
        self.assertIsInstance(optimal_strategy, str)
        print(f"Optimal Strategy: {optimal_strategy}")

if __name__ == "__main__":
    unittest.main()
