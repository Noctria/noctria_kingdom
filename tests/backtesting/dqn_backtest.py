import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from torch.utils.tensorboard import SummaryWriter

class DQNBacktest:
    """
    DQN の学習プロセスを可視化するバックテストツール
    - TensorBoard を活用し、損失推移・行動選択の変化を記録
    """

    def __init__(self, model, replay_buffer, optimizer, loss_fn, num_epochs=1000):
        """
        初期化
        :param model: DQN モデル
        :param replay_buffer: 経験リプレイバッファ
        :param optimizer: 最適化アルゴリズム
        :param loss_fn: 損失関数 (HuberLoss)
        :param num_epochs: トレーニング回数
        """
        self.model = model
        self.replay_buffer = replay_buffer
        self.optimizer = optimizer
        self.loss_fn = loss_fn
        self.num_epochs = num_epochs
        self.writer = SummaryWriter(log_dir="runs/dqn_backtest")

    def train(self, batch_size=32):
        """ バックテストの実行 """
        for epoch in range(self.num_epochs):
            if self.replay_buffer.size() < batch_size:
                continue  # バッファが十分に溜まるまで待機

            states, actions, rewards, next_states, dones, _, _ = self.replay_buffer.sample(batch_size)
            states_tensor = torch.tensor(states, dtype=torch.float32)
            next_states_tensor = torch.tensor(next_states, dtype=torch.float32)
            actions_tensor = torch.tensor(actions, dtype=torch.int64)
            rewards_tensor = torch.tensor(rewards, dtype=torch.float32)
            dones_tensor = torch.tensor(dones, dtype=torch.float32)

            # Q値の計算
            q_values = self.model(states_tensor)
            next_q_values = self.model(next_states_tensor).detach()

            # TDターゲットの計算
            target_q_values = q_values.clone()
            for i in range(batch_size):
                if dones[i]:
                    target_q_values[i, actions[i]] = rewards[i]
                else:
                    target_q_values[i, actions[i]] = rewards[i] + 0.99 * torch.max(next_q_values[i])

            # 損失計算と更新
            loss = self.loss_fn(q_values, target_q_values)
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()

            # TensorBoard に記録
            self.writer.add_scalar("Loss", loss.item(), epoch)

            if epoch % 100 == 0:
                print(f"Epoch {epoch}: Loss = {loss.item()}")

        self.writer.close()
