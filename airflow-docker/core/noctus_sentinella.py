import numpy as np
import pandas as pd
from data.market_data_fetcher import MarketDataFetcher
from core.risk_management import RiskManagement

class NoctusSentinella:
    """リスク管理と異常検知を行うAI（実際のヒストリカルデータ使用版・MetaAI対応）"""

    def __init__(self, risk_threshold=0.02, max_spread=0.018, min_liquidity=120):
        self.risk_threshold = risk_threshold
        self.max_spread = max_spread
        self.min_liquidity = min_liquidity
        self.market_fetcher = MarketDataFetcher()

        # ✅ ヒストリカルデータ取得（1時間足・1ヶ月分）
        data_array = self.market_fetcher.get_usdjpy_historical_data(interval="1h", period="1mo")
        if data_array is None:
            print("⚠️ データ取得失敗。ダミーデータで初期化します")
            data_array = np.random.normal(loc=100, scale=5, size=(100, 5))

        columns = ["Open", "High", "Low", "Close", "Volume"]
        historical_data = pd.DataFrame(data_array, columns=columns)
        self.risk_manager = RiskManagement(historical_data=historical_data)

    def process(self, market_data):
        if not isinstance(market_data, dict):
            print("⚠️ market_dataがlistなどで渡されました。空辞書に置換します")
            market_data = {}

        risk_score = self._calculate_risk(market_data)
        spread = market_data.get("spread", 0.0)
        liquidity = market_data.get("volume", 0.0)
        order_block_impact = market_data.get("order_block", 0.0)
        volatility = market_data.get("volatility", 0.0)

        if liquidity < self.min_liquidity or spread > self.max_spread:
            return "AVOID_TRADING"

        adjusted_risk_threshold = self.risk_threshold * (1 + order_block_impact)
        if risk_score > adjusted_risk_threshold and volatility > 0.2:
            return "REDUCE_RISK"
        else:
            return "MAINTAIN_POSITION"

    def _calculate_risk(self, market_data):
        price_history = market_data.get("price_history", [])
        price = market_data.get("price", 1.0)

        if not price_history:
            return 0.0

        risk_value = self.risk_manager.calculate_var()
        return risk_value / price if price != 0 else 0.0

if __name__ == "__main__":
    noctus_ai = NoctusSentinella()
    mock_market_data = {
        "price": 1.2530,
        "price_history": [1.2500, 1.2525, 1.2550, 1.2510, 1.2540],
        "spread": 0.015, "volume": 120, "order_block": 0.5, "volatility": 0.22
    }
    decision = noctus_ai.process(mock_market_data)
    print("Risk Management Decision:", decision)
