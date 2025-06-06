import numpy as np
import pandas as pd
from data.market_data_fetcher import MarketDataFetcher
from core.risk_management import RiskManagement

class NoctusSentinella:
    """
    MetaAI対応版:
    リスク管理と異常検知を担当するAIモジュール
    """

    def __init__(self, risk_threshold=0.02, max_spread=0.018, min_liquidity=120):
        self.risk_threshold = risk_threshold
        self.max_spread = max_spread
        self.min_liquidity = min_liquidity
        self.market_fetcher = MarketDataFetcher()

        # ✅ ヒストリカルデータ取得
        data_array = self.market_fetcher.get_usdjpy_historical_data(interval="1h", period="1mo")
        if data_array is None:
            print("⚠️ データ取得失敗。ダミーデータで初期化します")
            data_array = np.random.normal(loc=100, scale=5, size=(100, 5))

        columns = ["Open", "High", "Low", "Close", "Volume"]
        historical_data = pd.DataFrame(data_array, columns=columns)

        # ✅ リスク管理インスタンス
        self.risk_manager = RiskManagement(historical_data=historical_data)

    def _calculate_risk(self, market_data):
        """
        市場データからリスクスコアを計算
        （例: VaRを適用）
        """
        price_history = market_data.get("price_history", [])
        price = market_data.get("price", 1.0)  # 0除算防止で1.0に

        if not price_history:
            return 0.0

        volatility = np.std(price_history)
        risk_value = self.risk_manager.calculate_var()
        return risk_value / price if price != 0 else 0.0

    def decide_action(self, market_data):
        """
        ✅ MetaAI統合用インターフェース:
        市場データを受け取り、リスク管理戦略を決定
        """
        risk_score = self._calculate_risk(market_data)
        spread = market_data.get("spread", 0.0)
        liquidity = market_data.get("volume", 0.0)
        order_block_impact = market_data.get("order_block", 0.0)
        volatility = market_data.get("volatility", 0.0)

        # 流動性 & スプレッドチェック
        if liquidity < self.min_liquidity or spread > self.max_spread:
            return "AVOID_TRADING"

        # 大口注文の影響を加味してリスク基準を補正
        adjusted_risk_threshold = self.risk_threshold * (1 + order_block_impact)

        if risk_score > adjusted_risk_threshold and volatility > 0.2:
            return "REDUCE_RISK"
        else:
            return "MAINTAIN_POSITION"

# ✅ 改修後のテスト実行
if __name__ == "__main__":
    noctus_ai = NoctusSentinella()
    mock_market_data = {
        "price": 1.2530,
        "price_history": [1.2500, 1.2525, 1.2550, 1.2510, 1.2540],
        "spread": 0.015, "volume": 120, "order_block": 0.5, "volatility": 0.22
    }
    decision = noctus_ai.decide_action(mock_market_data)
    print("Risk Management Decision:", decision)
