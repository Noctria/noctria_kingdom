# core/meta_ai.py

import numpy as np

class MetaAI:
    """
    MetaAI: 複数の戦略AIを統合し、最終的なトレードアクションを決定する統括AIクラス
    """

    def __init__(self, strategy_agents):
        """
        各戦略AIを受け取り、統括管理する
        - strategy_agents: dict (例: {'Aurus': AurusSingularis(), ...})
        """
        self.strategy_agents = strategy_agents

    def decide_final_action(self, market_state):
        """
        各戦略AIからアクションを取得し、最終的なトレードアクションを決定する
        ➜ 今は単純に各戦略AIの出力を見て 'SELL' を優先、次に 'BUY'、なければ 'HOLD'。
        """
        strategy_actions = {
            name: agent.process(market_state)
            for name, agent in self.strategy_agents.items()
        }

        # デバッグ表示
        print("各戦略の出力:", strategy_actions)

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
        ➜ 将来的にはDQNやPPOに接続して学習更新を実装予定
        """
        print("=== MetaAI Learn Call ===")
        print(f"State: {state}")
        print(f"Action: {action}")
        print(f"Reward: {reward}")
        print(f"Next State: {next_state}")
        print(f"Done: {done}")
        print("=========================")

