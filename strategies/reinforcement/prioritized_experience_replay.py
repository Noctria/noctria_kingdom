import random
import numpy as np

class PrioritizedExperienceReplay:
    """
    TD誤差に基づいてサンプルの優先度を設定する経験リプレイバッファ
    - 優先度の高い経験を学習することで、効率的な強化学習を実現
    """

    def __init__(self, capacity=100000, alpha=0.6):
        """
        初期化
        :param capacity: バッファの最大容量
        :param alpha: 優先度のスケール係数（0に近いほどランダムサンプリングに近づく）
        """
        self.capacity = capacity
        self.buffer = []
        self.priorities = []
        self.alpha = alpha
        self.position = 0

    def store(self, state, action, reward, next_state, done, td_error):
        """
        経験をバッファに追加し、TD誤差に基づいて優先度を設定
        :param state: 現在の状態
        :param action: 実行した行動
        :param reward: 受けた報酬
        :param next_state: 次の状態
        :param done: エピソード終了フラグ
        :param td_error: TD誤差（優先度の指標）
        """
        priority = (abs(td_error) + 1e-5) ** self.alpha

        if len(self.buffer) < self.capacity:
            self.buffer.append(None)
            self.priorities.append(None)

        self.buffer[self.position] = (state, action, reward, next_state, done)
        self.priorities[self.position] = priority

        # 循環バッファのため、位置を更新
        self.position = (self.position + 1) % self.capacity

    def sample(self, batch_size):
        """
        優先度に基づいてバッファからサンプルを取得
        :param batch_size: 取得するサンプルの数
        :return: (states, actions, rewards, next_states, dones, weights, indices)
        """
        priorities = np.array(self.priorities)
        probs = priorities / priorities.sum()
        indices = np.random.choice(len(self.buffer), batch_size, p=probs)
        batch = [self.buffer[idx] for idx in indices]
        weights = (len(self.buffer) * probs[indices]) ** -1  # 重要度サンプリングの重み

        states, actions, rewards, next_states, dones = zip(*batch)
        return np.array(states), np.array(actions), np.array(rewards), np.array(next_states), np.array(dones), weights, indices

    def update_priorities(self, indices, td_errors):
        """
        TD誤差に基づいて優先度を更新
        :param indices: 更新対象のインデックス
        :param td_errors: 新しいTD誤差
        """
        for i, td_error in zip(indices, td_errors):
            self.priorities[i] = (abs(td_error) + 1e-5) ** self.alpha

    def size(self):
        """
        現在のバッファサイズを取得
        :return: バッファ内のサンプル数
        """
        return len(self.buffer)
