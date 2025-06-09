import gym
import numpy as np
import pandas as pd
from stable_baselines3 import PPO

# 🎯 カスタム報酬関数
def calculate_reward(profit, drawdown, win_rate):
    """
    Noctria Kingdom版報酬関数
    利益最大化 + ドローダウン抑制 + 勝率ボーナス
    """
    reward = profit
    max_drawdown_threshold = -30  # 例: -30pips以上でペナルティ
    if drawdown < max_drawdown_threshold:
        reward += drawdown
    if win_rate > 0.6:
        reward += 10
    return reward

class MetaAI(gym.Env):
    """
    MetaAI: 各戦略AIを統合し、強化学習による自己進化を行う（PPO統合版・ファンダメンタル拡張版）
    """

    def __init__(self, strategy_agents):
        super(MetaAI, self).__init__()

        self.strategy_agents = strategy_agents

        # ✅ データ読み込み（OHLCV + ファンダ）
        self.data = pd.read_csv("/opt/airflow/data/preprocessed_usdjpy_with_fundamental.csv", parse_dates=['datetime'])
        self.data.set_index('datetime', inplace=True)
        self.current_step = 0

        # ✅ 観測空間
        self.observation_space = gym.spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self.data.shape[1],),
            dtype=np.float32
        )

        # ✅ アクション空間
        self.action_space = gym.spaces.Discrete(3)

        self.ppo_agent = PPO("MlpPolicy", self, verbose=1)

        # トレード履歴
        self.trade_history = []
        self.max_drawdown = 0.0
        self.wins = 0
        self.trades = 0

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
        self.current_step += 1
        done = self.current_step >= len(self.data) - 1

        obs = self.data.iloc[self.current_step].values.astype(np.float32)

        # ✅ ダミーの取引結果（ここを実戦ロジックに置き換え予定）
        profit = np.random.uniform(-5, 5)
        spread_cost = np.random.uniform(0, 0.2)
        commission = 0.1

        self.trade_history.append(profit)

        # ✅ 最大ドローダウン計算
        cum_profit = np.cumsum(self.trade_history)
        peak = np.maximum.accumulate(cum_profit)
        drawdowns = peak - cum_profit
        self.max_drawdown = np.max(drawdowns)

        # ✅ 勝率計算（例: 収益がプラスなら勝ち）
        self.trades += 1
        if profit > 0:
            self.wins += 1
        win_rate = self.wins / self.trades if self.trades > 0 else 0.0

        # ✅ カスタム報酬関数でreward計算
        reward = calculate_reward(profit, -self.max_drawdown, win_rate)

        print(
            f"Action: {action}, Reward: {reward:.3f}, Drawdown: {self.max_drawdown:.3f}, "
            f"Win Rate: {win_rate:.2f}"
        )

        return obs, reward, done, {}

    def reset(self):
        self.current_step = 0
        self.trade_history.clear()
        self.max_drawdown = 0.0
        self.wins = 0
        self.trades = 0
        obs = self.data.iloc[self.current_step].values.astype(np.float32)
        return obs

    def learn(self, total_timesteps=5000):
        print("=== MetaAI PPO学習サイクル開始 ===")
        self.ppo_agent.learn(total_timesteps=total_timesteps)
        print("=== MetaAI PPO学習サイクル完了 ===")
