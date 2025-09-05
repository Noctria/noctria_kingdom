import gym
import numpy as np
import pandas as pd
from typing import List, Dict, Any

# MetaAIは純粋な「環境」となり、エージェント（PPO）は外部で定義・学習します。
class MetaAIEnv(gym.Env):
    """
    MetaAI: 各戦略AIの意見を観測し、最適な最終判断を下すことを学習する強化学習環境。
    """
    def __init__(self, df: pd.DataFrame, strategy_agents: List[Any], initial_balance: float = 100000.0, transaction_cost: float = 0.001):
        super(MetaAIEnv, self).__init__()

        self.df = df
        self.strategy_agents = strategy_agents
        self.initial_balance = initial_balance
        self.transaction_cost = transaction_cost

        # ★修正点: 観測空間を「市場データ + 戦略AIの出力」に拡張
        num_market_features = self.df.shape[1]
        num_strategy_signals = len(self.strategy_agents)
        self.observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf,
            shape=(num_market_features + num_strategy_signals,),
            dtype=np.float32
        )

        # アクション空間：0: HOLD, 1: BUY, 2: SELL
        self.action_space = gym.spaces.Discrete(3)

        self.reset()

    def _get_observation(self) -> np.ndarray:
        """現在の市場データと、各戦略AIの判断を結合して観測ベクトルを作成"""
        # 市場データ
        market_obs = self.df.iloc[self.current_step].values

        # 各戦略AIの判断（仮に-1:Sell, 0:Hold, 1:Buyとする）
        # 実際の .process() の戻り値に合わせて要調整
        strategy_obs = np.array([agent.process(market_obs) for agent in self.strategy_agents])

        # 結合して返す
        return np.concatenate([market_obs, strategy_obs]).astype(np.float32)

    def reset(self):
        """環境を初期状態にリセット"""
        self.current_step = 0
        self.balance = self.initial_balance
        self.net_worth_history = [self.initial_balance]
        self.current_position = 0  # 0: No position, 1: Long, -1: Short
        self.entry_price = 0
        
        return self._get_observation()

    def step(self, action: int):
        """エージェントの行動に基づき、環境を1ステップ進める"""
        self.current_step += 1
        done = self.current_step >= len(self.df) - 1

        # ★修正点: actionに基づいて実際の損益を計算
        current_price = self.df['close'].iloc[self.current_step]
        last_price = self.df['close'].iloc[self.current_step - 1]
        
        profit_loss = 0
        if self.current_position == 1: # Long position
            profit_loss = (current_price - last_price) * (self.balance / last_price)
        elif self.current_position == -1: # Short position
            profit_loss = (last_price - current_price) * (self.balance / last_price)

        self.balance += profit_loss
        
        # Actionの実行
        cost = 0
        if action == 1 and self.current_position != 1: # Buy
            self.current_position = 1
            self.entry_price = current_price
            cost = self.balance * self.transaction_cost
        elif action == 2 and self.current_position != -1: # Sell
            self.current_position = -1
            self.entry_price = current_price
            cost = self.balance * self.transaction_cost
        elif action == 0: # Hold
            self.current_position = 0

        self.balance -= cost
        self.net_worth_history.append(self.balance)

        # ★修正点: 現実的な報酬を計算
        # ここでは単純なシャープレシオ風の報酬を用いるが、より洗練させることも可能
        returns = np.diff(self.net_worth_history)
        if len(returns) > 1 and np.std(returns) != 0:
            sharpe_ratio = np.mean(returns) / np.std(returns)
            reward = sharpe_ratio
        else:
            reward = 0
            
        return self._get_observation(), reward, done, {}

# ================================================
# ✅ 学習と推論の実行例（このロジックは外部スクリプトやDAGに配置する）
# ================================================
if __name__ == '__main__':
    from stable_baselines3 import PPO

    # --- ダミーの戦略AI（四臣）を準備 ---
    class DummyAgent:
        def __init__(self, action_type):
            self.action_type = action_type
        def process(self, market_state):
            return self.action_type # 常に同じ判断を返す

    strategy_agents_list = [
        DummyAgent(1), # Aurusは常にBuy
        DummyAgent(-1), # Leviaは常にSell
        DummyAgent(0),  # Noctusは常にHold
    ]
    
    # --- データ準備 ---
    # 実際のパスに合わせて要調整
    df_path = "data/sample_test_data.csv"
    if not Path(df_path).exists():
        # ダミーデータ作成
        dates = pd.date_range(start="2024-01-01", periods=200)
        data = np.random.randn(200, 5).cumsum(axis=0)
        df_dummy = pd.DataFrame(data, index=dates, columns=['open', 'high', 'low', 'close', 'volume'])
        df_dummy.to_csv(df_path)
    
    df_main = pd.read_csv(df_path, index_col=0, parse_dates=True)

    # 1. 環境のインスタンス化
    print("1. 環境を初期化します...")
    env = MetaAIEnv(df=df_main, strategy_agents=strategy_agents_list)

    # 2. エージェントのインスタンス化と学習
    print("2. PPOエージェントを生成し、学習を開始します...")
    agent = PPO("MlpPolicy", env, verbose=1)
    agent.learn(total_timesteps=20000)
    
    # 3. 学習済みエージェントを使った推論（意思決定）
    print("\n3. 学習済みエージェントで意思決定を行います...")
    obs = env.reset()
    for _ in range(5):
        action, _states = agent.predict(obs, deterministic=True)
        action_map = {0: "HOLD", 1: "BUY", 2: "SELL"}
        print(f"   - MetaAIの最終判断: {action_map[action]}")
        obs, reward, done, info = env.step(action)
        if done:
            break
