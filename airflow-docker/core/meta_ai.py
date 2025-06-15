import gymnasium as gym
import numpy as np
import pandas as pd

from strategies.reward import calculate_reward
from institutions.central_bank_ai import CentralBankAI

class MetaAI(gym.Env):
    """
    MetaAI: 各戦略AIを統合し、強化学習による自己進化を行う環境
    """

    def __init__(self, strategy_agents, data_path="/opt/airflow/data/preprocessed_usdjpy_with_fundamental.csv", verbose=False):
        super().__init__()

        self.strategy_agents = strategy_agents
        self.central_bank = CentralBankAI()
        self.verbose = verbose

        # ✅ データ読み込み
        self.data = pd.read_csv(data_path, parse_dates=['datetime'])
        self.data.set_index('datetime', inplace=True)
        self.current_step = 0

        # ✅ 空間定義
        self.observation_space = gym.spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self.data.shape[1],),
            dtype=np.float32
        )
        self.action_space = gym.spaces.Discrete(3)  # 0: HOLD, 1: BUY, 2: SELL

        # ✅ トレード統計
        self.trade_history = []
        self.max_drawdown = 0.0
        self.wins = 0
        self.trades = 0

    def step(self, action):
        self.current_step += 1
        done = self.current_step >= len(self.data) - 1

        if done:
            obs = np.zeros(self.data.shape[1], dtype=np.float32)
            return obs, 0.0, done, {}

        obs = self.data.iloc[self.current_step].values.astype(np.float32)

        # ✅ 模擬利益
        profit = np.random.uniform(-5, 5)
        self.trade_history.append(profit)

        # ✅ 統計更新
        cum_profit = np.cumsum(self.trade_history)
        peak = np.maximum.accumulate(cum_profit)
        self.max_drawdown = np.max(peak - cum_profit)
        self.trades += 1
        if profit > 0:
            self.wins += 1
        win_rate = self.wins / self.trades if self.trades > 0 else 0.0
        recent_profits = self.trade_history[-10:]

        # ✅ ファンダメンタル情報
        current_row = self.data.iloc[self.current_step]
        fundamentals = {
            "cpi": current_row.get("cpi", 0.0),
            "interest_diff": current_row.get("interest_diff", 0.0),
            "unemployment": current_row.get("unemployment", 0.0),
        }
        cb_score = self.central_bank.get_policy_score(fundamentals)

        # ✅ カスタム報酬計算
        reward = calculate_reward(
            profit=profit,
            drawdown=-self.max_drawdown,
            win_rate=win_rate,
            recent_profits=recent_profits,
            cb_score=cb_score
        )

        if self.verbose:
            print(
                f"[Step {self.current_step}] Action: {action}, Reward: {reward:.3f}, "
                f"Drawdown: {self.max_drawdown:.2f}, Win Rate: {win_rate:.2%}, CB_Score: {cb_score:.2f}"
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

    def decide_final_action(self, market_state):
        """
        戦略AI群から多数決で最終アクション決定（リアル運用時用）
        """
        strategy_actions = {
            name: agent.process(market_state)
            for name, agent in self.strategy_agents.items()
        }

        if self.verbose:
            print("🧠 各戦略AIの提案:", strategy_actions)

        if "SELL" in strategy_actions.values():
            return 2
        elif "BUY" in strategy_actions.values():
            return 1
        return 0
