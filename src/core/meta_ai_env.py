# core/meta_ai_env.py

import gym
import numpy as np

class MetaAIEnv(gym.Env):
    """
    MetaAI向けの学習環境（OpenAI Gym形式）

    各戦略AIの出力と行動を統合し、
    強化学習アルゴリズムが学習できる環境を提供する。
    """

    def __init__(self):
        super(MetaAIEnv, self).__init__()

        # ✅ 観測空間（例: 12次元の市場状態）
        self.observation_space = gym.spaces.Box(low=-np.inf, high=np.inf, shape=(12,))

        # ✅ 行動空間（例: 0=SELL, 1=HOLD, 2=BUY）
        self.action_space = gym.spaces.Discrete(3)

        # ✅ 状態管理
        self.state = self._get_initial_state()
        self.current_step = 0
        self.max_steps = 1000

    def _get_initial_state(self):
        """
        初期状態（ダミー: ランダムベクトル）を生成
        """
        return np.random.rand(12)

    def reset(self):
        """
        環境のリセット
        """
        self.state = self._get_initial_state()
        self.current_step = 0
        return self.state

    def step(self, action):
        """
        行動を受け取り、次状態・報酬・終了判定・追加情報を返す
        """
        # ✅ 簡易版: ランダムに次状態を生成
        next_state = np.random.rand(12)

        # ✅ 簡易版: 行動に応じた報酬（SELL=-1, HOLD=0, BUY=+1）
        if action == 0:
            reward = -1
        elif action == 2:
            reward = 1
        else:
            reward = 0

        self.current_step += 1
        done = self.current_step >= self.max_steps

        # ✅ 状態更新
        self.state = next_state

        return next_state, reward, done, {}

    def render(self, mode='human'):
        """
        （オプション）環境の状態を可視化
        """
        print(f"Step: {self.current_step}, State: {self.state}")
