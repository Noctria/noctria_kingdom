import numpy as np
import tensorflow as tf
import gym
import shap
from stable_baselines3 import PPO, DDPG
from transformers import pipeline
from sklearn.ensemble import IsolationForest
from strategies.evolutionary.evolutionary_algorithm import GeneticAlgorithm
from execution.order_execution import OrderExecution
from data.market_data_fetcher import MarketDataFetcher
from data.lstm_data_processor import LSTMDataProcessor
from strategies.portfolio_optimizer import PortfolioOptimizer
from strategies.self_play import NoctriaSelfPlayAI

class NoctriaMasterAI(gym.Env):
    """
    MetaAI対応: Noctria Kingdom 統括AI
    - 市場データ分析
    - 自己進化型強化学習
    - ポートフォリオ最適化
    """

    def __init__(self):
        super(NoctriaMasterAI, self).__init__()

        # ✅ Observation / Action Space
        self.observation_space = gym.spaces.Box(low=-np.inf, high=np.inf, shape=(12,))
        self.action_space = gym.spaces.Box(low=-1.0, high=1.0, shape=(1,), dtype=np.float32)

        # ✅ 各コンポーネント
        self.market_fetcher = MarketDataFetcher()
        self.order_executor = OrderExecution()
        self.sentiment_model = pipeline("sentiment-analysis")
        self.evolutionary_agent = GeneticAlgorithm()
        self.anomaly_detector = IsolationForest(contamination=0.05)
        self.explainer = shap.Explainer(self._model_predict, self._get_sample_data())
        self.portfolio_optimizer = PortfolioOptimizer()
        self.lstm_processor = LSTMDataProcessor(window_size=30)
        self.self_play_ai = NoctriaSelfPlayAI()

        # ✅ 戦略パラメータ
        self.strategy_params = {
            "BUY_THRESHOLD": 0.6,
            "SELL_THRESHOLD": 0.4,
            "RISK_FACTOR": 1.0,
            "TREND_SENSITIVITY": 0.5,
        }

        # ✅ モデル群
        self.forecast_model = self._build_lstm_model()
        self.ppo_agent = PPO("MlpPolicy", self, verbose=0)
        self.ddpg_agent = DDPG("MlpPolicy", self, verbose=0)  # 将来的に切り替え可能

    def _build_lstm_model(self):
        """未来予測用LSTMモデル"""
        model = tf.keras.Sequential([
            tf.keras.layers.LSTM(50, return_sequences=True, input_shape=(30, 5)),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.LSTM(50),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(25, activation="relu"),
            tf.keras.layers.Dense(1, activation="linear")
        ])
        model.compile(optimizer="adam", loss="mse")
        return model

    def _model_predict(self, data):
        """SHAP用ダミー関数"""
        return np.random.rand(data.shape[0])

    def _get_sample_data(self):
        """SHAP用サンプルデータ"""
        return np.random.rand(100, 12)

    def adjust_risk_strategy(self, market_data):
        """異常検知によるリスク制御判断"""
        features = list(market_data.get("observation", [0.0]*12))
        features.append(market_data.get("price_change", 0.0))
        data = np.array(features).reshape(1, -1)

        self.anomaly_detector.fit(data)
        if self.anomaly_detector.predict(data)[0] == -1:
            return "REDUCE_POSITION"
        return "NORMAL"

    def predict_future_market(self, historical_data):
        """未来市場動向をLSTMで予測"""
        seq = self.lstm_processor.prepare_single_sequence(historical_data)
        prediction = self.forecast_model.predict(seq, verbose=0)
        score = (prediction[0][0] + 1) / 2
        return score

    def analyze_market(self, market_data):
        """
        市場データを受け取り、MetaAIとして総合的に分析し、
        各層（強化学習 / 予測モデル / リスク評価）から統合的に意思決定する。
        """
        observation = market_data.get("observation", np.zeros(12))
        historical_data = market_data.get("historical_prices", [])

        lstm_score = self.predict_future_market(historical_data)
        rl_action, _ = self.ppo_agent.predict(observation, deterministic=True)
        risk_level = self.adjust_risk_strategy(market_data)

        # ✅ 最終的な戦略アクション
        action = "hold"
        if lstm_score > self.strategy_params["BUY_THRESHOLD"]:
            action = "buy"
        elif lstm_score < self.strategy_params["SELL_THRESHOLD"]:
            action = "sell"

        return {
            "lstm_score": lstm_score,
            "rl_action": float(rl_action),
            "risk_level": risk_level,
            "market_sentiment": "bullish",   # ダミー
            "action": action,
            "symbol": "USDJPY",
            "lot": 0.1
        }

if __name__ == "__main__":
    ai = NoctriaMasterAI()
    dummy_data = {
        "observation": np.random.rand(12),
        "historical_prices": np.random.rand(100, 5),
        "price_change": 0.05
    }
    output = ai.analyze_market(dummy_data)
    print("AI戦略層の出力:", output)
