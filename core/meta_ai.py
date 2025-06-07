# core/meta_ai.py

import gym
import numpy as np
from stable_baselines3 import PPO

class MetaAI(gym.Env):
    """
    MetaAI: 各戦略AIを統合し、強化学習による自己進化を行う（PPO統合版）
    """

    def __init__(self, strategy_agents):
        super(MetaAI, self).__init__()

        self.strategy_agents = strategy_agents

        # ✅ 観測空間: 例として12次元の連続値
        self.observation_space = gym.spaces.Box(low=-np.inf, high=np.inf, shape=(12,))
        # ✅ アクション空間: 例として離散（0: HOLD, 1: BUY, 2: SELL）
        self.action_space = gym.spaces.Discrete(3)

        self.ppo_agent = PPO("MlpPolicy", self, verbose=1)

        # 例: 状態履歴や損益履歴（任意の追跡用）
        self.trade_history = []
        self.max_drawdown = 0.0

    def decide_final_action(self, market_state):
        """
        各戦略AIからアクションを取得し、最終アクションを決定
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
        環境の1ステップ進行と報酬計算（複合報酬式）
        """
        # 仮想の「市場変動」「利益/損失」「スプレッドコスト」など
        trade_profit = np.random.uniform(-5, 5)  # ±5pips相当のランダム損益
        spread_cost = np.random.uniform(0, 0.2)  # 例: スプレッドコスト
        commission = 0.1  # 例: 固定手数料

        # トレード履歴に追加
        self.trade_history.append(trade_profit)

        # 最大ドローダウン計算（例: 累積損益の最大DD）
        cum_profit = np.cumsum(self.trade_history)
        peak = np.maximum.accumulate(cum_profit)
        drawdowns = peak - cum_profit
        self.max_drawdown = np.max(drawdowns)

        # ✅ おすすめの複合報酬式
        reward = (
            0.6 * trade_profit
            - 0.3 * self.max_drawdown
            - 0.1 * (spread_cost + commission)
        )

        # 次の観測をダミーで生成（実際はデータベースから）
        obs = np.random.rand(12)
        done = False

        print(f"Action: {action}, Reward: {reward:.3f}, Drawdown: {self.max_drawdown:.3f}")

        return obs, reward, done, {}

    def reset(self):
        """
        環境の初期化
        """
        self.trade_history.clear()
        self.max_drawdown = 0.0
        return np.random.rand(12)

    def learn(self, total_timesteps=5000):
        """
        PPOによる自己進化サイクル
        """
        print("=== MetaAI PPO学習サイクル開始 ===")
        self.ppo_agent.learn(total_timesteps=total_timesteps)
        print("=== MetaAI PPO学習サイクル完了 ===")
