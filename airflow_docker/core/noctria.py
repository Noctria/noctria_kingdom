from core.path_config import *
# core/noctria.py

import sys
import os

import numpy as np
import pandas as pd
import logging

from strategies.aurus_singularis import AurusSingularis
from strategies.levia_tempest import LeviaTempest
from strategies.noctus_sentinella import NoctusSentinella
from strategies.prometheus_oracle import PrometheusOracle

from core.meta_ai import MetaAI
from core.risk_manager import RiskManager
from core.logger import setup_logger
from data.market_data_fetcher import MarketDataFetcher


class Noctria:
    """
    Noctria Kingdomの統合AI王：
    各AI臣下の出力を統合し、MetaAIによって最終判断を下す
    """

    def __init__(self):
        # ✅ ロガー設定
        self.logger = setup_logger("Noctria", "/opt/airflow/logs/Noctria.log")

        # ✅ データ取得と初期化
        self.market_fetcher = MarketDataFetcher()
        data_array = self.market_fetcher.get_usdjpy_historical_data(interval="1h", period="1mo")

        if data_array is None:
            self.logger.warning("⚠️ ヒストリカルデータ取得失敗。ダミーデータで初期化")
            data_array = np.random.normal(loc=100, scale=5, size=(100, 5))

        columns = ["Open", "High", "Low", "Close", "Volume"]
        historical_data = pd.DataFrame(data_array, columns=columns)

        self.risk_manager = RiskManagement(historical_data=historical_data)

        # ✅ 戦略AI（臣下）初期化
        self.aurus = AurusSingularis()
        self.levia = LeviaTempest()
        self.noctus = NoctusSentinella()
        self.prometheus = PrometheusOracle()

        # ✅ MetaAI（統合AI）構築
        self.meta_ai = MetaAI(strategy_agents={
            "Aurus": self.aurus,
            "Levia": self.levia,
            "Noctus": self.noctus,
            "Prometheus": self.prometheus
        })

    def analyze_market(self):
        """
        市場を分析し、MetaAIによって最終的な戦略を決定する
        """
        market_state = self._create_observation_vector()

        # ✅ 空間整合チェック（メンテナンス性向上）
        assert len(market_state) == self.meta_ai.observation_space.shape[0], \
            f"📉 観測ベクトル長がMetaAIと不一致: {len(market_state)} vs {self.meta_ai.observation_space.shape[0]}"

        final_action = self.meta_ai.decide_final_action(market_state)

        self.logger.info(f"MetaAI統合による最終戦略決定: {final_action}")
        return final_action

    def _create_observation_vector(self):
        """
        12次元の観測ベクトルを構築（ここではダミーデータ）
        今後: RSI, MA, ファンダ等を統合して拡張予定
        """
        return np.random.rand(12).tolist()

    def execute_trade(self):
        """
        最終決定戦略を元に、実行（ここではログ表示のみ）
        将来的にはリスク制御付き実行モジュールと統合予定
        """
        action = self.analyze_market()
        self.logger.info(f"💼 トレード実行（アクションID）: {action}")
        return f"Executing trade using: {action}"


# ✅ 単体テスト起動例
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    noctria_ai = Noctria()
    decision = noctria_ai.execute_trade()
    print(decision)
