"""
meta_ai_env_with_fundamentals.py
PPO強化学習エージェント用の環境クラス。
ファンダメンタルデータも観測空間に含めて、トレーディング環境を拡張する。
"""

import gymnasium as gym
import numpy as np
import pandas as pd

class TradingEnvWithFundamentals(gym.Env):
    def __init__(self, data_path):
        """
        Parameters:
        ----------
        data_path: str
            統合済みデータ（テクニカル + ファンダ）CSVファイルパス
        """
        self.data = pd.read_csv(data_path, parse_dates=['datetime'])
        self.data.set_index('datetime', inplace=True)
        self.current_step = 0

        # 観測空間（例: open, high, low, close, volume, cpi, interest_diff, unemployment）
        self.observation_space = gym.spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self.data.shape[1],),  # カラム数が観測次元
            dtype=np.float32
        )

        # 行動空間例（0=Hold, 1=Buy, 2=Sell）
        self.action_space = gym.spaces.Discrete(3)

    def reset(self, seed=None, options=None):
        self.current_step = 0
        return self._next_observation(), {}

    def step(self, action):
        """
        1ステップ進めるロジック。ここでは簡易版（リワードはダミー）。
        """
        self.current_step += 1
        done = self.current_step >= len(self.data) - 1

        # 簡易報酬: ダミー（後で報酬関数をカスタマイズ可）
        reward = 0.0

        return self._next_observation(), reward, done, False, {}

    def _next_observation(self):
        obs = self.data.iloc[self.current_step].values.astype(np.float32)
        return obs

    def render(self):
        pass  # 可視化不要な場合は空でOK

if __name__ == "__main__":
    # 簡単な動作確認
    env = TradingEnvWithFundamentals("data/preprocessed_usdjpy_with_fundamental.csv")
    obs, _ = env.reset()
    print("初期観測ベクトル:", obs)
