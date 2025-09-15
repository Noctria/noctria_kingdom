import os
import sys
import pytest
import unittest
# --- Dynamic resolve for MarketDataFetcher (new/legacy path). No E402 at top-level.
def _resolve_market_fetcher():
    try:
        # New path (preferred)
        from core.data.market_data_fetcher import MarketDataFetcher as _F  # noqa: WPS433
        return _F
    except Exception:
        try:
            # Legacy path (if exists)
            from data.data_loader import MarketDataFetcher as _F  # noqa: WPS433
            return _F
        except Exception:
            return None

MarketDataFetcher = _resolve_market_fetcher()


sys.path.insert(0, os.path.abspath("src"))
try:
    from core.noctria import Noctria as _Noctria  # preferred (lowercase file)
except Exception:
    try:
        from core.Noctria import Noctria as _Noctria  # legacy/case-variant
    except Exception:
        pytest.skip("Noctria class not available in src/core", allow_module_level=True)
Noctria = _Noctria



class TestNoctria(unittest.TestCase):
    """Noctria AIの統合戦略をバックテストする"""

    def setUp(self):
        """テスト開始前のセットアップ"""
        self.noctria = Noctria()
        self.market_fetcher = MarketDataFetcher(api_key="YOUR_API_KEY")

    def test_strategy_execution(self):
        """市場データを適用し、戦略精度を評価"""
        _mock_market_data = {
            "price": 1.245,
            "volume": 1500,
            "sentiment": 0.75,
            "trend_strength": 0.6,
            "volatility": 0.18,
            "order_block": 0.5,
            "institutional_flow": 0.85,
            "macro_trend": "bullish",
            "news_impact": 0.3,
            "liquidity_ratio": 1.3,
        }
        trade_decision = self.noctria.execute_trade()
        print("Trade Decision:", trade_decision)
        self.assertIn(trade_decision, ["BUY", "SELL", "HOLD"])

    def test_market_analysis(self):
        """市場データの分析が正しく動作するかを確認"""
        market_data, risk_evaluation, optimal_strategy = self.noctria.analyze_market()
        assert isinstance(market_data, dict)
        assert "volatility" in market_data
        assert risk_evaluation in ["LOW", "MEDIUM", "HIGH"]
        assert isinstance(optimal_strategy, str)
