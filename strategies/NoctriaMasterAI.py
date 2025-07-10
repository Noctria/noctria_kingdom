import numpy as np
import tensorflow as tf
import gym
import shap
from typing import Dict, Any
from stable_baselines3 import PPO, DDPG
from transformers import pipeline
from sklearn.ensemble import IsolationForest

from strategies.evolutionary.evolutionary_algorithm import GeneticAlgorithm
from execution.order_execution import OrderExecution
from core.data.market_data_fetcher import MarketDataFetcher
from core.data.lstm_data_processor import LSTMDataProcessor
from strategies.portfolio_optimizer import PortfolioOptimizer
from strategies.self_play import NoctriaSelfPlayAI


class NoctriaMasterAI(gym.Env):
    """
    🎓 Noctria Kingdom の統括AI
    - 市場の状態を観測し、自己進化型戦略を構築
    - 異常検知・LSTM予測・強化学習を統合
    """

    def __init__(self):
        print("NoctriaMasterAI: __init__ 開始")
        super().__init__()
        print("NoctriaMasterAI: super().__init__() 完了")

        # 🎯 強化学習用の空間設定（連続値）
        self.observation_space = gym.spaces.Box(low=-np.inf, high=np.inf, shape=(12,))
        self.action_space = gym.spaces.Box(low=-1.0, high=1.0, shape=(1,), dtype=np.float32)

        # 🔌 外部AI／ツール群の初期化
        self.market_fetcher = MarketDataFetcher()
        self.order_executor = OrderExecution()
        self.sentiment_model = pipeline("sentiment-analysis")
        self.evolutionary_agent = GeneticAlgorithm()
        self.anomaly_detector = IsolationForest(contamination=0.05)
        self.lstm_processor = LSTMDataProcessor(window_size=30)
        self.self_play_ai = NoctriaSelfPlayAI()
        self.portfolio_optimizer = PortfolioOptimizer()

        # ✅ SHAPによる解釈モデル（軽量な疑似予測関数を使う）
        sample_data = self._get_sample_data()
        self.explainer = shap.Explainer(self._model_predict, sample_data)

        # 🎯 戦略パラメータ
        self.strategy_params = {
            "BUY_THRESHOLD": 0.6,
            "SELL_THRESHOLD": 0.4,
            "RISK_FACTOR": 1.0,
            "TREND_SENSITIVITY": 0.5,
        }

        # 🔮 LSTM予測モデルの構築
        self.forecast_model = self.build_lstm_model()

        # 🧠 強化学習エージェント（PPO/DDPG）を初期化
        self.ppo_agent = PPO("MlpPolicy", self, verbose=0)
        self.ddpg_agent = DDPG("MlpPolicy", self, verbose=0)

    def build_lstm_model(self) -> tf.keras.Model:
        """未来市場予測用のLSTMモデル構築"""
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

    def _model_predict(self, data: np.ndarray) -> np.ndarray:
        """SHAP用の疑似モデル関数"""
        return np.random.rand(data.shape[0])

    def _get_sample_data(self) -> np.ndarray:
        """SHAP用のサンプルデータ生成"""
        return np.random.rand(100, 12)

    def adjust_risk_strategy(self, market_data: Dict[str, Any]) -> str:
        """異常値検知に基づきリスク調整"""
        features = []

        obs = market_data.get("observation", [])
        if isinstance(obs, (list, np.ndarray)):
            features.extend(list(obs))
        else:
            features.append(obs)

        if "price_change" in market_data:
            features.append(market_data["price_change"])

        data = np.array(features).reshape(1, -1)
        if self.anomaly_detector.predict(data)[0] == -1:
            return "REDUCE_POSITION"
        return "NORMAL"

    def predict_future_market(self, historical_data: np.ndarray) -> float:
        """LSTMモデルを用いて未来市場スコアを予測"""
        predict_seq = self.lstm_processor.prepare_single_sequence(historical_data)
        prediction = self.forecast_model.predict(predict_seq, verbose=0)
        score = (prediction[0][0] + 1) / 2  # 0.0〜1.0 にスケーリング
        return float(score)

    def analyze_market(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        市場状況を受け取り、戦略アクションを出力
        - LSTM予測
        - RL行動予測
        - 異常検知
        """
        if not isinstance(market_data, dict):
            print("⚠️ market_dataがlistなどで渡されました。空辞書に置換します")
            market_data = {}

        observation = market_data.get("observation", np.zeros(12))
        historical_data = market_data.get("historical_prices", np.zeros((30, 5)))

        lstm_score = self.predict_future_market(historical_data)
        rl_action, _ = self.ppo_agent.predict(observation, deterministic=True)
        risk_level = self.adjust_risk_strategy(market_data)

        # 💡 スコアに応じたアクション判定
        action = "hold"
        if lstm_score > self.strategy_params["BUY_THRESHOLD"]:
            action = "buy"
        elif lstm_score < self.strategy_params["SELL_THRESHOLD"]:
            action = "sell"

        return {
            "lstm_score": lstm_score,
            "rl_action": float(rl_action),
            "risk_level": risk_level,
            "market_sentiment": "bullish",  # ダミー
            "action": action,
            "symbol": "USDJPY",
            "lot": 0.1,
        }


# ✅ スタンドアロンテスト用
if __name__ == "__main__":
    env = NoctriaMasterAI()
    dummy_data = {
        "observation": np.random.rand(12),
        "historical_prices": np.random.rand(100, 5),
        "price_change": 0.05
    }
    output = env.analyze_market(dummy_data)
    print("AI戦略層の出力:", output)
