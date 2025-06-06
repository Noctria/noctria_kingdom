# core/meta_ai.py

import gym
import numpy as np
from stable_baselines3 import PPO

class MetaAI(gym.Env):
    """
    MetaAI: 複数の戦略AIを統合し、最終的なトレードアクションを決定する統括AIクラス（PPO強化学習統合版）
    """

    def __init__(self, strategy_agents):
        super(MetaAI, self).__init__()

        # 各戦略AIを管理
        self.strategy_agents = strategy_agents

        # ✅ 観測空間: 例として12次元の連続値
        self.observation_space = gym.spaces.Box(low=-np.inf, high=np.inf, shape=(12,))
        # ✅ アクション空間: 例として離散（0: HOLD, 1: BUY, 2: SELL）
        self.action_space = gym.spaces.Discrete(3)

        # ✅ PPOエージェントを初期化
        self.ppo_agent = PPO("MlpPolicy", self, verbose=1)

    def decide_final_action(self, market_state):
        """
        各戦略AIからアクションを取得し、最終アクションを決定
        ➜ 今は単純に各戦略AIの出力を集約し、SELL優先 → BUY優先 → HOLD。
        """
        strategy_actions = {
            name: agent.process(market_state)
            for name, agent in self.strategy_agents.items()
        }

        print("各戦略の出力:", strategy_actions)

        if "SELL" in strategy_actions.values():
            return 2  # SELL
        elif "BUY" in strategy_actions.values():
            return 1  # BUY
        else:
            return 0  # HOLD

    def step(self, action):
        """
        環境の1ステップを進める。
        例: 簡易的な報酬ロジックと次状態生成。
        """
        reward = np.random.uniform(-1, 1)  # 例: ±1.0のランダム報酬
        obs = np.random.rand(12)           # 新しい観測（ランダム）
        done = False                       # ここでは常に継続

        return obs, reward, done, {}

    def reset(self):
        """
        環境の初期化時に呼ばれる。
        """
        return np.random.rand(12)

    def learn(self, total_timesteps=1000):
        """
        PPOを使った学習サイクルの実行。
        """
        print("=== MetaAI PPO学習サイクル開始 ===")
        self.ppo_agent.learn(total_timesteps=total_timesteps)
        print("=== MetaAI PPO学習サイクル完了 ===")
