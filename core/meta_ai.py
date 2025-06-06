# core/meta_ai.py

import torch
import torch.nn as nn
import torch.optim as optim

class MetaAI:
    """
    王 (Noctria) の役割：複数AI（臣下）の結果を重み付け統合するメタAI層。
    """

    def __init__(self, strategy_agents, state_dim, learning_rate=1e-4):
        """
        strategy_agents: {'Aurus': agentA, 'Levia': agentB, ...} 各戦略AI
        state_dim: 市場状態ベクトルの次元数
        """
        self.strategy_agents = strategy_agents
        self.meta_policy = self._init_meta_network(state_dim, len(strategy_agents))
        self.optimizer = optim.Adam(self.meta_policy.parameters(), lr=learning_rate)
        self.gamma = 0.99  # 割引率（将来報酬の重み）

    def _init_meta_network(self, input_dim, output_dim):
        """
        メタポリシーネット（戦略の重み決定ネットワーク）
        """
        return nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, output_dim),
            nn.Softmax(dim=-1)  # 各戦略への信頼度（重み）に変換
        )

    def decide_final_action(self, market_state):
        """
        各戦略AIの行動を統合し、メタAIが最終戦略を決定
        """
        # 各戦略AIの行動を取得
        strategy_actions = {name: agent.decide_action(market_state)
                            for name, agent in self.strategy_agents.items()}

        # メタポリシーの入力（例：市場状態ベクトル）
        state_tensor = torch.tensor(market_state, dtype=torch.float32).unsqueeze(0)
        strategy_weights = self.meta_policy(state_tensor).detach().numpy()[0]

        # 最も重みが高い戦略の行動を採用
        selected_strategy = max(zip(strategy_actions.keys(), strategy_weights),
                                key=lambda x: x[1])[0]
        final_action = strategy_actions[selected_strategy]

        return final_action, strategy_weights

    def update_meta_policy(self, state, reward):
        """
        メタポリシーの更新ステップ（方策勾配のシンプル版）
        """
        state_tensor = torch.tensor(state, dtype=torch.float32).unsqueeze(0)
        weights = self.meta_policy(state_tensor)
        log_prob = torch.log(weights.max())  # 採用戦略の重みの最大値を強化
        loss = -log_prob * reward

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
