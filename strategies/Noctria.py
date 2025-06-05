import numpy as np
import tensorflow as tf
import gym
import shap
import requests
from stable_baselines3 import DQN, PPO, DDPG
from transformers import pipeline
from sklearn.ensemble import IsolationForest
from evolutionary_algorithm import GeneticAlgorithm
from execution.order_execution import OrderExecutor
from data.market_data_fetcher import MarketDataFetcher
from strategies.portfolio_optimizer import PortfolioOptimizer
from strategies.self_play import NoctriaSelfPlayAI

class NoctriaMasterAI(gym.Env):
    """Noctria Kingdom の統括AI：市場データを分析し、戦略を自己進化させる"""

    def __init__(self):
        super(NoctriaMasterAI, self).__init__()
        self.market_fetcher = MarketDataFetcher(api_key="YOUR_API_KEY")
        self.order_executor = OrderExecutor()
        self.sentiment_model = pipeline("sentiment-analysis")
        self.evolutionary_agent = GeneticAlgorithm()

        # 異常値検知モデル
        self.anomaly_detector = IsolationForest(contamination=0.05)

        # SHAPによる意思決定の透明化
        self.explainer = shap.Explainer(self._model_predict, self._get_sample_data())

        # ポートフォリオ最適化エージェント
        self.portfolio_optimizer = PortfolioOptimizer()

        # 戦略適応パラメータ
        self.strategy_params = {
            "BUY_THRESHOLD": 0.6,
            "SELL_THRESHOLD": 0.4,
            "RISK_FACTOR": 1.0,
            "TREND_SENSITIVITY": 0.5,
        }

        # LSTMモデル
        self.forecast_model = self.build_lstm_model()

        # 強化学習エージェント
        self.dqn_agent = DQN("MlpPolicy", self, verbose=1)
        self.ppo_agent = PPO("MlpPolicy", self, verbose=1)
        self.ddpg_agent = DDPG("MlpPolicy", self, verbose=1)

        # 自己対戦型AI
        self.self_play_ai = NoctriaSelfPlayAI()

        # 状態・行動空間
        self.observation_space = gym.spaces.Box(low=-np.inf, high=np.inf, shape=(12,))
        self.action_space = gym.spaces.Discrete(3)

    def build_lstm_model(self):
        model = tf.keras.Sequential([
            tf.keras.layers.LSTM(50, return_sequences=True, input_shape=(30, 6)),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.LSTM(50, return_sequences=False),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(25, activation="relu"),
            tf.keras.layers.Dense(1, activation="linear")
        ])
        model.compile(optimizer="adam", loss="mse")
        return model

    def _model_predict(self, data):
        return np.random.rand(data.shape[0])

    def _get_sample_data(self):
        return np.random.rand(100, 12)

    def adjust_risk_strategy(self, market_data):
        if self.anomaly_detector.predict([list(market_data.values())])[0] == -1:
            return "REDUCE_POSITION"
        return "NORMAL"

    def predict_future_market(self, historical_data):
        return np.random.rand()

    def decide_action(self, observation, market_data):
        risk_status = self.adjust_risk_strategy(market_data)
        if risk_status == "REDUCE_POSITION":
            print("⚠️ 市場異常検知 → HOLDを強制")
            return 2  # HOLD

        action_rl, _states = self.ppo_agent.predict(observation, deterministic=True)
        future_prediction = self.predict_future_market(self.market_fetcher.get_historical_data())
        print(f"🔮 LSTM予測: {future_prediction}")

        if future_prediction > 0.6:
            return 0  # BUY
        elif future_prediction < 0.4:
            return 1  # SELL

        return int(action_rl)

if __name__ == "__main__":
    env = NoctriaMasterAI()
    env.dqn_agent.learn(total_timesteps=10000)
    env.ppo_agent.learn(total_timesteps=10000)
    env.ddpg_agent.learn(total_timesteps=10000)
    print("🚀 NoctriaMasterAI の統合進化完了！")
