import numpy as np
import tensorflow as tf
import gym
import shap
import requests
from stable_baselines3 import DQN, PPO, DDPG
from transformers import pipeline
from sklearn.ensemble import IsolationForest
from strategies.evolutionary.evolutionary_algorithm import GeneticAlgorithm
from execution.order_execution import OrderExecution
from data.market_data_fetcher import MarketDataFetcher
from data.lstm_data_processor import LSTMDataProcessor
from strategies.portfolio_optimizer import PortfolioOptimizer
from strategies.self_play import NoctriaSelfPlayAI

class NoctriaMasterAI(gym.Env):
    """Noctria Kingdom の統括AI：市場データを分析し、戦略を自己進化させる"""

    def __init__(self):
        super(NoctriaMasterAI, self).__init__()
        self.market_fetcher = MarketDataFetcher()
        self.order_executor = OrderExecutor()
        self.sentiment_model = pipeline("sentiment-analysis")
        self.evolutionary_agent = GeneticAlgorithm()

        self.anomaly_detector = IsolationForest(contamination=0.05)
        self.explainer = shap.Explainer(self._model_predict, self._get_sample_data())
        self.portfolio_optimizer = PortfolioOptimizer()
        self.lstm_processor = LSTMDataProcessor(window_size=30)

        self.strategy_params = {
            "BUY_THRESHOLD": 0.6,
            "SELL_THRESHOLD": 0.4,
            "RISK_FACTOR": 1.0,
            "TREND_SENSITIVITY": 0.5,
        }

        self.forecast_model = self.build_lstm_model()
        self.dqn_agent = DQN("MlpPolicy", self, verbose=1)
        self.ppo_agent = PPO("MlpPolicy", self, verbose=1)
        self.ddpg_agent = DDPG("MlpPolicy", self, verbose=1)
        self.self_play_ai = NoctriaSelfPlayAI()

        self.observation_space = gym.spaces.Box(low=-np.inf, high=np.inf, shape=(12,))
        self.action_space = gym.spaces.Discrete(3)

    def build_lstm_model(self):
        model = tf.keras.Sequential([
            tf.keras.layers.LSTM(50, return_sequences=True, input_shape=(30, 5)),
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
        """異常値検知結果を返す（例: REDUCE_POSITION or NORMAL）"""
        if self.anomaly_detector.predict([list(market_data.values())])[0] == -1:
            return "REDUCE_POSITION"
        return "NORMAL"

    def predict_future_market(self, historical_data):
        """LSTMモデルで未来市場スコアを予測"""
        predict_seq = self.lstm_processor.create_predict_sequence(historical_data)
        prediction = self.forecast_model.predict(predict_seq)
        score = (prediction[0][0] + 1) / 2
        return score

    def analyze_market(self, market_data):
        """
        市場データを受け取り、AIモデル群の結果を統合して返す。
        core/Noctria.py から呼び出されるインターフェース
        """
        # 例: observation データは EA戦略が渡す
        observation = market_data.get("observation", np.zeros(12))
        historical_data = market_data.get("historical_prices", [])

        # AI戦略群の結果
        lstm_score = self.predict_future_market(historical_data)
        rl_action, _ = self.ppo_agent.predict(observation, deterministic=True)
        risk_level = self.adjust_risk_strategy(market_data)

        return {
            "lstm_score": lstm_score,
            "rl_action": int(rl_action),
            "risk_level": risk_level,
            "market_sentiment": "bullish"  # ダミーデータ、必要に応じて修正
        }

if __name__ == "__main__":
    env = NoctriaMasterAI()
    # 例: テスト用のダミーデータ
    dummy_data = {
        "observation": np.random.rand(12),
        "historical_prices": np.random.rand(100, 5),
        "price_change": 0.05
    }
    output = env.analyze_market(dummy_data)
    print("AI戦略層の出力:", output)
