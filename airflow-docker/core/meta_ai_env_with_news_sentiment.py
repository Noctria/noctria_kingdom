import gym
import numpy as np
import pandas as pd
from core.news_sentiment_fetcher import NewsSentimentFetcher

class MetaAIEnv(gym.Env):
    """
    ニュースセンチメント統合版のトレーディング環境
    """

    def __init__(self, data_path, api_key):
        super(MetaAIEnv, self).__init__()

        self.data = pd.read_csv(data_path, parse_dates=['datetime'])
        self.data.set_index('datetime', inplace=True)
        self.current_step = 0

        self.news_fetcher = NewsSentimentFetcher(api_key=api_key)

        self.observation_space = gym.spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self.data.shape[1] + 1,),
            dtype=np.float32
        )

        self.action_space = gym.spaces.Discrete(3)

        self.trade_history = []
        self.max_drawdown = 0.0
        self.wins = 0
        self.trades = 0

    def reset(self, seed=None, options=None):
        self.current_step = 0
        self.trade_history.clear()
        self.max_drawdown = 0.0
        self.wins = 0
        self.trades = 0
        return self._next_observation(), {}

    def step(self, action):
        self.current_step += 1
        done = self.current_step >= len(self.data) - 1

        sentiment_score = self.news_fetcher.fetch_latest_sentiment()
        obs_values = self.data.iloc[self.current_step].values.astype(np.float32)
        obs = np.append(obs_values, sentiment_score)

        profit = np.random.uniform(-5, 5)
        self.trade_history.append(profit)

        cum_profit = np.cumsum(self.trade_history)
        peak = np.maximum.accumulate(cum_profit)
        drawdowns = peak - cum_profit
        self.max_drawdown = np.max(drawdowns)

        self.trades += 1
        if profit > 0:
            self.wins += 1
        win_rate = self.wins / self.trades if self.trades > 0 else 0.0

        reward = profit + 0.1 * sentiment_score

        print(
            f"Step: {self.current_step}, Action: {action}, Profit: {profit:.2f}, "
            f"Sentiment: {sentiment_score}, Reward: {reward:.2f}, "
            f"Drawdown: {self.max_drawdown:.2f}, WinRate: {win_rate:.2f}"
        )

        return obs, reward, done, False, {}

    def _next_observation(self):
        sentiment_score = self.news_fetcher.fetch_latest_sentiment()
        obs_values = self.data.iloc[self.current_step].values.astype(np.float32)
        obs = np.append(obs_values, sentiment_score)
        return obs

    def render(self):
        pass


if __name__ == "__main__":
    import os
    api_key = os.getenv("NEWS_API_KEY", "YOUR_NEWSAPI_KEY")
    env = MetaAIEnv(
        data_path="/opt/airflow/data/preprocessed_usdjpy_with_fundamental.csv",
        api_key=api_key
    )
    obs, _ = env.reset()
    print("初期観測ベクトル:", obs)

    for _ in range(3):
        action = env.action_space.sample()
        obs, reward, done, _, _ = env.step(action)
        if done:
            break
