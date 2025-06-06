import numpy as np
from strategies.Aurus_Singularis import AurusSingularis
from strategies.Levia_Tempest import LeviaTempest
from strategies.Noctus_Sentinella import NoctusSentinella
from strategies.Prometheus_Oracle import PrometheusOracle

class MetaAI:
    """
    MetaAI：複数の戦略AIを統括し、最適な戦略を決定する統合AI層。
    """

    def __init__(self):
        self.aurus = AurusSingularis()
        self.levia = LeviaTempest()
        self.noctus = NoctusSentinella()
        self.prometheus = PrometheusOracle()

    def decide_final_action(self, market_state):
        """
        それぞれの戦略AIからの提案を集約し、最終アクションを決定する。
        """

        # それぞれの戦略AIからアクションを取得
        strategy_actions = {
            "AurusSingularis": self.aurus.process(market_state),
            "LeviaTempest": self.levia.process(market_state),
            "NoctusSentinella": self.noctus.process(market_state),
            "PrometheusOracle": self.prometheus.predict_market(market_state)
        }

        print("=== 各戦略AIの出力 ===")
        for name, action in strategy_actions.items():
            print(f"{name}: {action}")

        # 例として、ここでは最も積極的なBUYシグナルがあればBUYを返す
        if strategy_actions["AurusSingularis"] == "BUY":
            return "BUY"
        elif strategy_actions["LeviaTempest"] == "BUY":
            return "BUY"
        elif strategy_actions["NoctusSentinella"] == "REDUCE_RISK":
            return "HOLD"
        else:
            return "HOLD"

# ✅ 簡単なテスト
if __name__ == "__main__":
    meta_ai = MetaAI()
    mock_market_data = {
        "price": 1.2345,
        "previous_price": 1.2330,
        "volume": 200,
        "spread": 0.012,
        "order_block": 0.4,
        "volatility": 0.15,
        "sentiment": 0.8,
        "trend_strength": 0.7,
        "price_history": [1.23, 1.235, 1.238, 1.236, 1.234],
        "institutional_flow": 0.8,
        "short_interest": 0.5,
        "momentum": 0.9,
        "trend_prediction": 0.6,
        "liquidity_ratio": 1.2
    }
    final_decision = meta_ai.decide_final_action(mock_market_data)
    print("\n=== MetaAIの最終決定 ===")
    print("Final Decision:", final_decision)
