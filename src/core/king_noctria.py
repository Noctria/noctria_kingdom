# king_noctria.py

import numpy as np
import tensorflow as tf
import shap
from typing import Dict, Any

from stable_baselines3 import PPO, DDPG
from sklearn.ensemble import IsolationForest
from transformers import pipeline

from strategies.evolutionary.evolutionary_algorithm import GeneticAlgorithm
from strategies.portfolio_optimizer import PortfolioOptimizer
from strategies.self_play import NoctriaSelfPlayAI
from core.data.market_data_fetcher import MarketDataFetcher
from core.data.lstm_data_processor import LSTMDataProcessor
from execution.order_execution import OrderExecution


class KingNoctria:
    """
    👑 Noctria Kingdom 統治AI（王）
    - 各臣下の提案を受け取り、統合的に評価・決裁を行う
    - LSTM予測、強化学習、異常検知、SHAP解釈を組み合わせた最終意思決定器
    """

    def __init__(self):
        self.proposals: Dict[str, Any] = {}
        self.history: list[Dict[str, Any]] = []

        # モジュール初期化（臣下機能）
        self.market_fetcher = MarketDataFetcher()
        self.order_executor = OrderExecution()
        self.sentiment_model = pipeline("sentiment-analysis")
        self.evolutionary_agent = GeneticAlgorithm()
        self.self_play_ai = NoctriaSelfPlayAI()
        self.portfolio_optimizer = PortfolioOptimizer()
        self.lstm_processor = LSTMDataProcessor(window_size=30)
        self.anomaly_detector = IsolationForest(contamination=0.05)

        # 強化学習エージェント
        self.ppo_agent = PPO("MlpPolicy", self._dummy_env(), verbose=0)
        self.ddpg_agent = DDPG("MlpPolicy", self._dummy_env(), verbose=0)

        # LSTMモデルとSHAP
        self.forecast_model = self._build_lstm_model()
        self.explainer = shap.Explainer(self._model_predict, self._get_sample_data())

        # 戦略パラメータ
        self.strategy_params = {
            "BUY_THRESHOLD": 0.6,
            "SELL_THRESHOLD": 0.4,
            "RISK_FACTOR": 1.0,
        }

    # ======================
    # 🧠 決裁フロー
    # ======================

    def receive_proposals(self, proposals: Dict[str, Any]):
        """各臣下からの提案を受け取る"""
        self.proposals = proposals

    def decide_action(self) -> Dict[str, Any]:
        """
        提案・観測データを統合して王の意思決定を行う
        - 各手法（LSTM、RL、異常検知）を総合評価
        """
        market_data = self.proposals.get("market_data", {})
        observation = market_data.get("observation", np.zeros(12))
        historical = market_data.get("historical_prices", np.zeros((30, 5)))

        lstm_score = self._predict_future_market(historical)
        rl_action, _ = self.ppo_agent.predict(observation, deterministic=True)
        risk_level = self._adjust_risk_strategy(market_data)

        # 最終アクション決定
        action = "hold"
        if lstm_score > self.strategy_params["BUY_THRESHOLD"]:
            action = "buy"
        elif lstm_score < self.strategy_params["SELL_THRESHOLD"]:
            action = "sell"

        result = {
            "action": action,
            "lstm_score": float(lstm_score),
            "rl_action": float(rl_action),
            "risk_level": risk_level,
            "symbol": market_data.get("symbol", "USDJPY"),
            "lot": 0.1,
        }

        self.history.append(result)
        return result

    def explain_decision(self) -> Dict[str, Any]:
        """SHAPによる可視化用データ出力（GUI統合用）"""
        sample_data = self._get_sample_data()
        shap_values = self.explainer(sample_data[:5])
        return {
            "feature_names": [f"f{i}" for i in range(12)],
            "values": shap_values.values.tolist(),
            "base_value": float(shap_values.base_values[0]),
        }

    # ======================
    # 🔧 内部処理
    # ======================

    def _adjust_risk_strategy(self, market_data: Dict[str, Any]) -> str:
        features = list(market_data.get("observation", []))
        if "price_change" in market_data:
            features.append(market_data["price_change"])
        data = np.array(features).reshape(1, -1)
        return "REDUCE_POSITION" if self.anomaly_detector.predict(data)[0] == -1 else "NORMAL"

    def _predict_future_market(self, historical_data: np.ndarray) -> float:
        sequence = self.lstm_processor.prepare_single_sequence(historical_data)
        prediction = self.forecast_model.predict(sequence, verbose=0)
        return float((prediction[0][0] + 1) / 2)

    def _model_predict(self, data: np.ndarray) -> np.ndarray:
        return np.random.rand(data.shape[0])

    def _get_sample_data(self) -> np.ndarray:
        return np.random.rand(100, 12)

    def _build_lstm_model(self) -> tf.keras.Model:
        model = tf.keras.Sequential([
            tf.keras.layers.LSTM(50, return_sequences=True, input_shape=(30, 5)),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.LSTM(50),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(25, activation="relu"),
            tf.keras.layers.Dense(1, activation="linear"),
        ])
        model.compile(optimizer="adam", loss="mse")
        return model

    def _dummy_env(self):
        """強化学習用の仮想環境（PPO/DDPG初期化用）"""
        from gym import spaces
        class DummyEnv:
            observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(12,))
            action_space = spaces.Box(low=-1.0, high=1.0, shape=(1,), dtype=np.float32)
        return DummyEnv()


# ✅ スタンドアロンテスト
if __name__ == "__main__":
    king = KingNoctria()
    dummy_proposals = {
        "market_data": {
            "observation": np.random.rand(12),
            "historical_prices": np.random.rand(30, 5),
            "price_change": 0.03,
        }
    }
    king.receive_proposals(dummy_proposals)
    result = king.decide_action()
    print("📣 王Noctriaの決裁結果:", result)
