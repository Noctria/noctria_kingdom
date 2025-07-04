import gym
import numpy as np
import pandas as pd
from core.news_sentiment_fetcher import NewsSentimentFetcher
from typing import Optional, Tuple, Dict


class MetaAIEnv(gym.Env):
    """
    ニュースセンチメント統合型トレーディング環境
    - 観測空間: OHLCV + CPIなど + センチメントスコア
    - 行動空間: 0=HOLD, 1=BUY, 2=SELL
    """

    def __init__(self, data_path: str, api_key: str):
        super().__init__()

        self.data = pd.read_csv(data_path, parse_dates=["datetime"])
        self.data.set_index("datetime", inplace=True)
        self.current_step = 0

        self.news_fetcher = NewsSentimentFetcher(api_key=api_key)
        self.obs_dim = self.data.shape[1] + 1  # +1 for sentiment

        self.observation_space = gym.spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self.obs_dim,),
            dtype=np.float32
        )

        self.action_space = gym.spaces.Discrete(3)

        self.trade_history = []
        self.max_drawdown = 0.0
        self.wins = 0
        self.trades = 0

    def reset(self, seed: Optional[int] = None, options: Optional[dict] = None) -> Tuple[np.ndarray, Dict]:
        self.current_step = 0
        self.trade_history.clear()
        self.max_drawdown = 0.0
        self.wins = 0
        self.trades = 0
        return self._get_obs(), {}

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        self.current_step += 1
        done = self.current_step >= len(self.data) - 1

        if done:
            obs = np.zeros(self.obs_dim, dtype=np.float32)
            return obs, 0.0, done, False, {}

        obs = self._get_obs()

        # ✅ ダミー利益
        profit = np.random.uniform(-5, 5)
        self.trade_history.append(profit)

        # ✅ 統計計算
        cum_profit = np.cumsum(self.trade_history)
        peak = np.maximum.accumulate(cum_profit)
        drawdowns = peak - cum_profit
        self.max_drawdown = np.max(drawdowns)

        self.trades += 1
        if profit > 0:
            self.wins += 1
        win_rate = self.wins / self.trades if self.trades > 0 else 0.0

        sentiment_score = obs[-1]
        reward = profit + 0.1 * sentiment_score

        print(
            f"Step: {self.current_step:3d} | Action: {action} | Profit: {profit:+.2f} | "
            f"Sentiment: {sentiment_score:+.2f} | Reward: {reward:+.2f} | "
            f"DD: {self.max_drawdown:.2f} | WinRate: {win_rate:.2%}"
        )

        return obs, reward, done, False, {}

    def _get_obs(self) -> np.ndarray:
        try:
            sentiment_score = self.news_fetcher.fetch_latest_sentiment()
        except Exception as e:
            print(f"⚠️ Sentiment fetch failed: {e}")
            sentiment_score = 0.0

        obs_values = self.data.iloc[self.current_step].values.astype(np.float32)
        return np.append(obs_values, sentiment_score)

    def render(self):
        print(f"[Render] Step: {self.current_step}")


if __name__ == "__main__":
    import os
    api_key = os.getenv("NEWS_API_KEY", "YOUR_NEWSAPI_KEY")

    env = MetaAIEnv(
        data_path="/opt/airflow/data/preprocessed_usdjpy_with_fundamental.csv",
        api_key=api_key
    )

    obs, _ = env.reset()
    print("✅ 初期観測ベクトル:", obs)

    for _ in range(3):
        action = env.action_space.sample()
        obs, reward, done, _, _ = env.step(action)
        if done:
            break
