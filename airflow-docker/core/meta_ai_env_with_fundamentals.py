"""
meta_ai_env_with_fundamentals.py
PPO強化学習エージェント用の環境クラス。
ファンダメンタルデータも観測空間に含めて、トレーディング環境を拡張する。
"""

import gymnasium as gym
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Optional


class TradingEnvWithFundamentals(gym.Env):
    def __init__(self, data_path: str):
        """
        Parameters:
        ----------
        data_path: str
            テクニカル + ファンダメンタル統合済みデータのCSVパス
        """
        self.data = pd.read_csv(data_path, parse_dates=["datetime"])
        self.data.set_index("datetime", inplace=True)
        self.current_step = 0
        self.obs_dim = self.data.shape[1]

        # ✅ 観測空間（テクニカル + ファンダ指標）
        self.observation_space = gym.spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self.obs_dim,),
            dtype=np.float32
        )

        # ✅ 行動空間（0: Hold, 1: Buy, 2: Sell）
        self.action_space = gym.spaces.Discrete(3)

    def reset(self, seed: Optional[int] = None, options: Optional[dict] = None) -> Tuple[np.ndarray, Dict]:
        """
        環境のリセット
        """
        self.current_step = 0
        return self._next_observation(), {}

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        1ステップ進める（簡易版）
        """
        self.current_step += 1
        done = self.current_step >= len(self.data) - 1

        # ✅ ダミー報酬（将来の改良対象）
        reward = 0.0
        # TODO: action, market変化、過去成績から reward を決定する

        return self._next_observation(), reward, done, False, {}

    def _next_observation(self) -> np.ndarray:
        """
        現ステップの観測データを返す
        """
        obs = self.data.iloc[self.current_step].values.astype(np.float32)
        return obs

    def render(self, mode: str = "human"):
        """
        簡易可視化（任意）
        """
        print(f"[Step {self.current_step}]")



if __name__ == "__main__":
    # ✅ 単体テスト
    env = TradingEnvWithFundamentals("data/preprocessed_usdjpy_with_fundamental.csv")
    obs, _ = env.reset()
    print("✅ 初期観測ベクトル:", obs)
