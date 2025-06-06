# core/meta_ai.py

import numpy as np

class MetaAI:
    def __init__(self, strategy_agents=None, state_dim=12, action_dim=3):
        """
        MetaAI: 各戦略AIの統合管理・最終意思決定を行うクラス

        Parameters:
        -----------
        strategy_agents : dict
            例: {
                "AurusSingularis": AurusSingularisインスタンス,
                "LeviaTempest": LeviaTempestインスタンス,
                ...
            }
        state_dim : int
            状態ベクトルの次元数（例: 12）
        action_dim : int
            行動空間の次元数（例: 3）
        """
        if strategy_agents is None:
            strategy_agents = {}
        self.strategy_agents = strategy_agents
        self.state_dim = state_dim
        self.action_dim = action_dim

    def decide_final_action(self, market_state):
        """
        各戦略AIに市場状態を渡し、その結果をまとめる。
        現状は単純にランダム選択しているが、
        実際には統合アルゴリズムや多数決などに置き換え可能。
        """
        # 各戦略AIの出力を取得
        strategy_actions = {
            name: agent.process(market_state)
            for name, agent in self.strategy_agents.items()
        }

        # 例としてランダムに最終行動を決定（統合ルールを組み込む想定）
        final_action = np.random.choice(["BUY", "SELL", "HOLD"])
        return final_action, strategy_actions
