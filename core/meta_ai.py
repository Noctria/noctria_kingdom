import numpy as np

class MetaAI:
    """MetaAI: 複数の戦略AIを統合し、最終的なトレードアクションを決定する統括AIクラス"""

    def __init__(self, strategy_agents):
        self.strategy_agents = strategy_agents  # 例: {'Aurus': AurusSingularis(), ...}
        # ここに将来的に強化学習（例: Qテーブル、DQNなど）を統合する余地がある

    def decide_final_action(self, market_state):
        """
        各戦略AIからアクションを取得し、最終的なトレードアクションを決定する
        ➜ 今は単純に各戦略AIの出力を見て 'SELL' を優先、次に 'BUY'、なければ 'HOLD'。
        """
        strategy_actions = {
            name: agent.process(market_state)
            for name, agent in self.strategy_agents.items()
        }

        if "SELL" in strategy_actions.values():
            final_action = "SELL"
        elif "BUY" in strategy_actions.values():
            final_action = "BUY"
        else:
            final_action = "HOLD"

        return final_action

    def learn(self, state, action, reward, next_state, done):
        """
        テスト用のダミー学習メソッド
        本番ではDQNやPPOに接続し、経験の蓄積と更新を行う
        """
        print("=== MetaAI Learn Call ===")
        print(f"State: {state}")
        print(f"Action: {action}")
        print(f"Reward: {reward}")
        print(f"Next State: {next_state}")
        print(f"Done: {done}")
        print("=========================")

