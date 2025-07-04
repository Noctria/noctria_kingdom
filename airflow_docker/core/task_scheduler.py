import logging
import numpy as np
from typing import Dict

from strategies.aurus_singularis import AurusSingularis
from strategies.levia_tempest import LeviaTempest
from strategies.noctus_sentinella import NoctusSentinella
from strategies.prometheus_oracle import PrometheusOracle


class TaskScheduler:
    """
    市場環境に基づき最適戦略を選定・実行する統合モジュール
    """

    def __init__(self):
        self.logger = logging.getLogger("TaskScheduler")
        self.logger.setLevel(logging.DEBUG)

        # ✅ 戦略オブジェクト（臣下たち）
        self.strategies = {
            "trend_analysis": AurusSingularis(),
            "scalping": LeviaTempest(),
            "risk_management": NoctusSentinella(),
            "market_prediction": PrometheusOracle(),
        }

    def score_strategies(self, market_data: Dict[str, float]) -> str:
        """
        各AI戦略の評価スコアを算出し、最も優れた戦略を返す
        """
        strategy_scores = {}

        for name, strategy in self.strategies.items():
            base_score = strategy.evaluate(market_data)

            risk_adjustment = -abs(market_data.get("volatility", 0.0)) * 0.5
            sentiment_boost = market_data.get("news_sentiment", 0.0) * 0.3

            total_score = base_score + risk_adjustment + sentiment_boost
            strategy_scores[name] = total_score

            self.logger.debug(f"{name} → Base: {base_score:.2f}, RiskAdj: {risk_adjustment:.2f}, "
                              f"SentimentBoost: {sentiment_boost:.2f}, Total: {total_score:.2f}")

        best_strategy = max(strategy_scores, key=strategy_scores.get)
        self.logger.info(f"🎯 Selected Optimal Strategy: {best_strategy}")
        return best_strategy

    def dispatch_trade(self, strategy_name: str, market_data: Dict[str, float]) -> None:
        """
        選定された戦略に基づいてトレード処理を行う（例示実装）
        """
        strategy = self.strategies.get(strategy_name)
        if not strategy:
            self.logger.warning(f"❌ Unknown strategy: {strategy_name}")
            return

        result = strategy.execute(market_data)
        self.logger.info(f"🛠️ Strategy {strategy_name} executed with result: {result}")


# ✅ テスト実行例
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    scheduler = TaskScheduler()
    mock_market_data = {
        "price_change": 0.02,
        "volatility": 0.03,
        "liquidity_index": 0.7,
        "news_sentiment": 0.6
    }

    selected = scheduler.score_strategies(mock_market_data)
    scheduler.dispatch_trade(selected, mock_market_data)
