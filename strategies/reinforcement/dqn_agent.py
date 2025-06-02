import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np

class DQNAgent:
    def __init__(self, state_dim, action_dim, learning_rate=1e-4, gamma=0.99):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma

        # ネットワーク定義
        self.model = nn.Sequential(
            nn.Linear(state_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Linear(128, action_dim)
        )

        # 最適化アルゴリズム (Adam)
        self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate, betas=(0.9, 0.999))

    def decide_action(self, state, epsilon=0.1):
        """ ε-greedy を用いて行動を決定 """
        if np.random.rand() < epsilon:
            return np.random.randint(self.action_dim)  # ランダム行動
        with torch.no_grad():
            state_tensor = torch.tensor(state, dtype=torch.float32)
            q_values = self.model(state_tensor)
        return torch.argmax(q_values).item()  # 最適行動

    def update(self, batch):
        """ 経験をリプレイし、DQN を学習 """
        states, actions, rewards, next_states, dones = batch

        # Q値の計算
        q_values = self.model(torch.tensor(states, dtype=torch.float32))
        next_q_values = self.model(torch.tensor(next_states, dtype=torch.float32))

        # TDターゲットの計算
        target_q_values = q_values.clone().detach()
        for i in range(len(dones)):
            if dones[i]:
                target_q_values[i, actions[i]] = rewards[i]
            else:
                target_q_values[i, actions[i]] = rewards[i] + self.gamma * torch.max(next_q_values[i])

        # 損失計算と更新
        loss = nn.MSELoss()(q_values, target_q_values)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
