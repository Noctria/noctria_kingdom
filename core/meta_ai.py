import gym
import numpy as np
import pandas as pd
from stable_baselines3 import PPO

class MetaAI(gym.Env):
    """
    MetaAI: 各戦略AIを統合し、強化学習（PPO）により自己進化する知性体。
    ➤ ファンダメンタル要素（CPI, 失業率, 金利差）も学習に反映。
    """

    def __init__(self, strategy_agents):
        super(MetaAI, self).__init__()
        self.strategy_agents = strategy_agents

        # ✅ データ読み込み（OHLCV + ファンダ）
        self.data = pd.read_csv("/opt/airflow/data/preprocessed_usdjpy_with_fundamental.csv", parse_dates=["datetime"])
        self.data.set_index("datetime", inplace=True)
        self.current_step = 0

        # ✅ 観測空間：カラム数に応じたベクトル（無限範囲）
        self.observation_space = gym.spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self.data.shape[1],),
            dtype=np.float32
        )

        # ✅ アクション空間：離散（0: HOLD, 1: BUY, 2: SELL）
        self.action_space = gym.spaces.Discrete(3)

        # ✅ PPO学習器
        self.ppo_agent = PPO("MlpPolicy", self, verbose=1)

        # トレード履歴
        self.trade_history = []
        self.max_drawdown = 0.0

    def decide_final_action(self, market_state: dict) -> int:
        """
        登録済みの各戦略AIの出力を収集し、最終アクションを決定する。
        """
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

    def step(self, action: int):
        # ステップ進行
        self.current_step += 1
        done = self.current_step >= len(self.data) - 1

        # ✅ 現時点の観測データ
        obs = self.data.iloc[self.current_step].values.astype(np.float32)

        # ✅ ファンダ要素
        cpi = self.data.iloc[self.current_step]["cpi"]
        interest_diff = self.data.iloc[self.current_step]["interest_diff"]
        unemployment = self.data.iloc[self.current_step]["unemployment"]

        # ✅ ダミー利益とコスト（→後で実収益ロジックに差し替え）
        trade_profit = np.random.uniform(-5, 5)
        spread_cost = np.random.uniform(0, 0.2)
        commission = 0.1

        self.trade_history.append(trade_profit)

        # ✅ 最大ドローダウン更新
        cum_profit = np.cumsum(self.trade_history)
        peak = np.maximum.accumulate(cum_profit)
        drawdowns = peak - cum_profit
        self.max_drawdown = np.max(drawdowns)

        # ✅ ファンダ寄与項（例：CPI上昇はボーナス、失業率上昇はペナルティ）
        cpi_factor = 0.05 * (cpi / 100)
        unemployment_factor = -0.05 * (unemployment / 10)

        # ✅ 直近の連勝・連敗によるバイアス
        recent_trades = self.trade_history[-3:]
        streak_sum = sum(recent_trades)
        streak_bonus = 0.1 if streak_sum > 0 else -0.1 if streak_sum < 0 else 0

        # ✅ 複合報酬式
        reward = (
            0.6 * trade_profit
            - 0.3 * self.max_drawdown
            - 0.1 * (spread_cost + commission)
            + cpi_factor
            + unemployment_factor
            + streak_bonus
        )

        print(
            f"Action: {action}, Reward: {reward:.3f}, Drawdown: {self.max_drawdown:.3f}, "
            f"CPI: {cpi:.2f}, Unemployment: {unemployment:.2f}, Streak: {streak_sum:.2f}"
        )

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
