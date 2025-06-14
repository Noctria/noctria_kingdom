# core/noctria.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
import numpy as np
import pandas as pd

from strategies.aurus_singularis import AurusSingularis
from strategies.levia_tempest import LeviaTempest
from strategies.noctus_sentinella import NoctusSentinella
from strategies.prometheus_oracle import PrometheusOracle
from core.meta_ai import MetaAI
from data.market_data_fetcher import MarketDataFetcher
from core.risk_management import RiskManagement


class Noctria:
    """Noctria Kingdomの統合AI王：複数AIの結果を統合し、最適戦略を決定"""

    def __init__(self):
        self.logger = logging.getLogger("Noctria")

        # ✅ MarketDataFetcherでヒストリカルデータ取得
        self.market_fetcher = MarketDataFetcher()
        data_array = self.market_fetcher.get_usdjpy_historical_data(interval="1h", period="1mo")

        if data_array is None:
            self.logger.warning("⚠️ ヒストリカルデータ取得失敗。ダミーデータで初期化")
            data_array = np.random.normal(loc=100, scale=5, size=(100, 5))

        columns = ["Open", "High", "Low", "Close", "Volume"]
        historical_data = pd.DataFrame(data_array, columns=columns)

        self.risk_manager = RiskManagement(historical_data=historical_data)

        # 各戦略AI（臣下）
        self.aurus = AurusSingularis()
        self.levia = LeviaTempest()
        self.noctus = NoctusSentinella()
        self.prometheus = PrometheusOracle()

        # ✅ MetaAI統合
        self.meta_ai = MetaAI(
            strategy_agents={
                "Aurus": self.aurus,
                "Levia": self.levia,
                "Noctus": self.noctus,
                "Prometheus": self.prometheus
            }
        )

    def analyze_market(self):
        """
        市場データ取得 → 各戦略の決定を集約 → MetaAIで最終戦略を決定
        """
        market_state = self._create_observation_vector()

        # ✅ MetaAIが最終戦略を決定
        final_action = self.meta_ai.decide_final_action(market_state)

        self.logger.info(f"MetaAI統合の最終戦略: {final_action}")

        return final_action

    def _create_observation_vector(self):
        """
        12次元の観測ベクトル例（ここでは単純にランダムダミーでテスト）
        """
        return np.random.rand(12).tolist()

    def execute_trade(self):
        """
        最終的な戦略を実行（ここではログ表示だけ）
        """
        action = self.analyze_market()
        self.logger.info(f"Executing trade: {action}")
        return f"Executing trade using: {action}"


# ✅ テスト起動例
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    noctria_ai = Noctria()
    decision = noctria_ai.execute_trade()
    print(decision)
