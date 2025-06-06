import numpy as np
import gym

class MetaAI:
    """各戦略AIの出力を統合し、最終的な戦略を決定するMeta AI"""

    def __init__(self, agents):
        self.agents = agents
        self.observation_space = gym.spaces.Box(low=-np.inf, high=np.inf, shape=(12,))
        self.action_space = gym.spaces.Discrete(3)  # 0: HOLD, 1: BUY, 2: SELL

    def decide_final_action(self, market_state):
        """各戦略AIの出力を集約して最終アクションを決定"""
        strategy_actions = {name: agent.process(market_state) for name, agent in self.agents.items()}

        if "AVOID_TRADING" in strategy_actions.values() or "REDUCE_RISK" in strategy_actions.values():
            return "HOLD"

        if list(strategy_actions.values()).count("BUY") > list(strategy_actions.values()).count("SELL"):
            return "BUY"
        elif list(strategy_actions.values()).count("SELL") > list(strategy_actions.values()).count("BUY"):
            return "SELL"

        return "HOLD"

# ✅ テスト用サンプル
if __name__ == "__main__":
    class DummyAgent:
        def process(self, market_state):
            return np.random.choice(["BUY", "SELL", "HOLD"])

    agents = {
        "AurusSingularis": DummyAgent(),
        "LeviaTempest": DummyAgent(),
        "NoctusSentinella": DummyAgent(),
        "PrometheusOracle": DummyAgent()
    }

    meta_ai = MetaAI(agents)
    mock_state = {"price": 1.25, "volume": 100}
    decision = meta_ai.decide_final_action(mock_state)
    print("MetaAI Decision:", decision)
