import gym
import numpy as np
import pandas as pd
from stable_baselines3 import PPO

from strategies.reward import calculate_reward
from institutions.central_bank_ai import CentralBankAI

class MetaAI(gym.Env):
    """
    MetaAI: 各戦略AIを統合し、強化学習による自己進化を行う（PPO統合版・中央銀行AI対応）
    """

    def __init__(self, strategy_agents):
        super(MetaAI, self).__init__()

        self.strategy_agents = strategy_agents
        self.central_bank = CentralBankAI()

        # ✅ データ読み込み（OHLCV + ファンダメンタル）
        self.data = pd.read_csv("/opt/airflow/data/preprocessed_usdjpy_with_fundamental.csv", parse_dates=['datetime'])
        self.data.set_index('datetime', inplace=True)
        self.current_step = 0

        # ✅ 観測空間（OHLCV + CPI等の拡張指標を含む）
        self.observation_space = gym.spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self.data.shape[1],),
            dtype=np.float32
        )

        # ✅ アクション空間（0: HOLD, 1: BUY, 2: SELL）
        self.action_space = gym.spaces.Discrete(3)

        # ✅ PPO学習用エージェント
        self.ppo_agent = PPO("MlpPolicy", self, verbose=1)

        # トレード履歴・パフォーマンス統計
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

        # ✅ 模擬取引結果（後で本番ロジックへ置換）
        profit = np.random.uniform(-5, 5)
        self.trade_history.append(profit)

        # ✅ 最大ドローダウン計算
        cum_profit = np.cumsum(self.trade_history)
        peak = np.maximum.accumulate(cum_profit)
        drawdowns = peak - cum_profit
        self.max_drawdown = np.max(drawdowns)

        # ✅ 勝率計算
        self.trades += 1
        if profit > 0:
            self.wins += 1
        win_rate = self.wins / self.trades if self.trades > 0 else 0.0

        recent_profits = self.trade_history[-10:]

        # ✅ ファンダメンタル情報取得（CPI・金利差・失業率など）
        current_row = self.data.iloc[self.current_step]
        fundamental_data = {
            "cpi": current_row.get("cpi", 0.0),
            "interest_diff": current_row.get("interest_diff", 0.0),
            "unemployment": current_row.get("unemployment", 0.0)
        }

        cb_score = self.central_bank.get_policy_score(fundamental_data)

        # ✅ カスタム報酬関数（中央銀行スコア反映）
        reward = calculate_reward(
            profit=profit,
            drawdown=-self.max_drawdown,
            win_rate=win_rate,
            recent_profits=recent_profits,
            cb_score=cb_score
        )

        print(
            f"Action: {action}, Reward: {reward:.3f}, Drawdown: {self.max_drawdown:.3f}, "
            f"Win Rate: {win_rate:.2f}, CB_Score: {cb_score:.2f}"
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
