import gym
import numpy as np
import pandas as pd
from stable_baselines3 import PPO

class MetaAI(gym.Env):
    """
    MetaAI: 各戦略AIを統合し、強化学習による自己進化を行う（PPO統合版・ファンダメンタル拡張版）
    """

    def __init__(self, strategy_agents):
        super(MetaAI, self).__init__()

        self.strategy_agents = strategy_agents

        # ✅ データ読み込み（OHLCV + ファンダ）
        self.data = pd.read_csv("data/preprocessed_usdjpy_with_fundamental.csv", parse_dates=['datetime'])
        self.data.set_index('datetime', inplace=True)
        self.current_step = 0

        # ✅ 観測空間: データカラム数に合わせる
        self.observation_space = gym.spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self.data.shape[1],),
            dtype=np.float32
        )

        # ✅ アクション空間: 例として離散（0: HOLD, 1: BUY, 2: SELL）
        self.action_space = gym.spaces.Discrete(3)

        self.ppo_agent = PPO("MlpPolicy", self, verbose=1)

        # トレード履歴
        self.trade_history = []
        self.max_drawdown = 0.0

    def decide_final_action(self, market_state):
        strategy_actions = {
            name: agent.process(market_state)
            for name, agent in self.strategy_agents.items()
        }
        print("各戦略の出力:", strategy_actions)
        if "SELL" in strategy_actions.values():
            return 2
        elif "BUY" in strategy_actions.values():
            return 1
        else:
            return 0

    def step(self, action):
        # ステップ進行
        self.current_step += 1
        done = self.current_step >= len(self.data) - 1

        # ✅ 実際の観測ベクトル
        obs = self.data.iloc[self.current_step].values.astype(np.float32)

        # ✅ ダミー報酬（後で本物に置換）
        trade_profit = np.random.uniform(-5, 5)
        spread_cost = np.random.uniform(0, 0.2)
        commission = 0.1

        self.trade_history.append(trade_profit)

        cum_profit = np.cumsum(self.trade_history)
        peak = np.maximum.accumulate(cum_profit)
        drawdowns = peak - cum_profit
        self.max_drawdown = np.max(drawdowns)

        reward = (
            0.6 * trade_profit
            - 0.3 * self.max_drawdown
            - 0.1 * (spread_cost + commission)
        )

        print(f"Action: {action}, Reward: {reward:.3f}, Drawdown: {self.max_drawdown:.3f}")
        return obs, reward, done, {}

    def reset(self):
        self.current_step = 0
        self.trade_history.clear()
        self.max_drawdown = 0.0
        obs = self.data.iloc[self.current_step].values.astype(np.float32)
        return obs

    def learn(self, total_timesteps=5000):
        print("=== MetaAI PPO学習サイクル開始 ===")
        self.ppo_agent.learn(total_timesteps=total_timesteps)
        print("=== MetaAI PPO学習サイクル完了 ===")
