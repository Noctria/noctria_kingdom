import gym
import numpy as np
from typing import Tuple, Dict


class MetaAIEnv(gym.Env):
    """
    MetaAI向けの学習環境（OpenAI Gym形式）

    各戦略AIの出力と行動を統合し、
    強化学習アルゴリズムが学習できる環境を提供する。
    """

    def __init__(self):
        super().__init__()

        # ✅ 状態・行動空間
        self.state_dim = 12
        self.observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf, shape=(self.state_dim,), dtype=np.float32
        )
        self.action_space = gym.spaces.Discrete(3)  # 0=SELL, 1=HOLD, 2=BUY

        self.reward_map = {0: -1.0, 1: 0.0, 2: 1.0}  # ✅ 行動別報酬マップ

        # ✅ 状態管理
        self.state = self._get_initial_state()
        self.current_step = 0
        self.max_steps = 1000

    def _get_initial_state(self) -> np.ndarray:
        """
        初期状態を生成（ダミー: ランダムベクトル）
        """
        return np.random.rand(self.state_dim).astype(np.float32)

    def reset(self) -> np.ndarray:
        """
        環境のリセット
        """
        self.state = self._get_initial_state()
        self.current_step = 0
        return self.state

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        行動を受け取り、次状態・報酬・終了判定・追加情報を返す
        """
        self.current_step += 1
        done = self.current_step >= self.max_steps

        next_state = np.random.rand(self.state_dim).astype(np.float32) if not done else np.zeros(self.state_dim, dtype=np.float32)

        reward = self.reward_map.get(action, 0.0)

        self.state = next_state
        return next_state, reward, done, {}

    def render(self, mode: str = 'human'):
        """
        環境の状態を可視化
        """
        print(f"Step: {self.current_step}, State: {self.state}")
