import numpy as np

class MetaAI:
    """
    各戦略AIを束ねて統合的な意思決定を行うメタAIクラス。
    """

    def __init__(self, strategy_agents=None):
        # ✅ 外部から渡されなければデフォルト戦略群を生成
        if strategy_agents is not None:
            self.strategy_agents = strategy_agents
        else:
            from strategies.Aurus_Singularis import AurusSingularis
            from strategies.Levia_Tempest import LeviaTempest
            from strategies.Noctus_Sentinella import NoctusSentinella
            from strategies.Prometheus_Oracle import PrometheusOracle

            self.strategy_agents = {
                "AurusSingularis": AurusSingularis(),
                "LeviaTempest": LeviaTempest(),
                "NoctusSentinella": NoctusSentinella(),
                "PrometheusOracle": PrometheusOracle()
            }

    def decide_final_action(self, market_state):
        """
        各戦略AIの出力を統合して、最終的なアクションを決定する。
        """
        strategy_actions = {}
        for name, agent in self.strategy_agents.items():
            # 各戦略AIにprocess()を持たせておく（MetaAI用に決め打ち）
            if hasattr(agent, "process"):
                action = agent.process(market_state)
            else:
                # 万一 process() がない場合は "HOLD"
                action = "HOLD"
            strategy_actions[name] = action

        # ✅ ここでは多数決的に BUY/SELL が多い方を返すシンプルな例
        buy_count = sum(1 for a in strategy_actions.values() if a == "BUY")
        sell_count = sum(1 for a in strategy_actions.values() if a == "SELL")

        if buy_count > sell_count:
            final_action = "BUY"
        elif sell_count > buy_count:
            final_action = "SELL"
        else:
            final_action = "HOLD"

        return final_action, strategy_actions

# ✅ テスト実行例
if __name__ == "__main__":
    meta_ai = MetaAI()
    dummy_market_data = {
        "price": 1.2345,
        "previous_price": 1.2300,
        "volume": 130,
        "spread": 0.012,
        "order_block": 0.3,
        "volatility": 0.15
    }
    final_action, details = meta_ai.decide_final_action(dummy_market_data)
    print("MetaAI Final Action:", final_action)
    print("Details by strategy:", details)
