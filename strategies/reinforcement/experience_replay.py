import random
import numpy as np

class ExperienceReplay:
    def __init__(self, capacity=100000):
        """ 経験を蓄積するリプレイバッファ """
        self.capacity = capacity
        self.buffer = []
        self.position = 0

    def add(self, state, action, reward, next_state, done):
        """ 新しい経験をバッファに追加 """
        if len(self.buffer) < self.capacity:
            self.buffer.append(None)
        self.buffer[self.position] = (state, action, reward, next_state, done)
        self.position = (self.position + 1) % self.capacity  # 循環バッファ

    def sample(self, batch_size):
        """ バッファからランダムにサンプルを取得 """
        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        return np.array(states), np.array(actions), np.array(rewards), np.array(next_states), np.array(dones)

    def size(self):
        """ 現在のバッファサイズを取得 """
        return len(self.buffer)
