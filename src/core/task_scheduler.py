import logging
import numpy as np
from strategies import Aurus_Singularis, Levia_Tempest, Noctus_Sentinella, Prometheus_Oracle

class TaskScheduler:
    """市場環境に基づき、最適戦略を選択する統合モジュール"""

    def __init__(self):
        self.logger = logging.getLogger("TaskScheduler")
        self.logger.setLevel(logging.DEBUG)
        self.strategies = {
            "trend_analysis": Aurus_Singularis(),
            "scalping": Levia_Tempest(),
            "risk_management": Noctus_Sentinella(),
            "market_prediction": Prometheus_Oracle(),
        }

    def score_strategies(self, market_data):
        """市場データをAIへ適用し、最適戦略を動的選定"""

        state = np.array([market_data["price_change"], market_data["volatility"], market_data["liquidity_index"], market_data["news_sentiment"], 1])
        strategy_scores = {}

        for name, strategy in self.strategies.items():
            score = strategy.evaluate(market_data)
            risk_adjustment = -abs(market_data["volatility"]) * 0.5  
            sentiment_boost = market_data["news_sentiment"] * 0.3  
            strategy_scores[name] = score + risk_adjustment + sentiment_boost

        best_strategy = max(strategy_scores, key=strategy_scores.get)
        self.logger.info(f"Selected Optimal Strategy: {best_strategy}")
        return best_strategy

# ✅ `task_scheduler.py` の戦略最適化テスト
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    scheduler = TaskScheduler()
    mock_market_data = {"price_change": 0.02, "volatility": 0.03, "liquidity_index": 0.7, "news_sentiment": 0.6}

    selected_strategy = scheduler.score_strategies(mock_market_data)
    scheduler.dispatch_trade(selected_strategy, mock_market_data)
