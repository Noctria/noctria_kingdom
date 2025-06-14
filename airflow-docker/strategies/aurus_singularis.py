# /opt/airflow/strategies/aurus_singularis.py

import numpy as np
import pandas as pd
import tensorflow as tf
from data.market_data_fetcher import MarketDataFetcher
from core.risk_management import RiskManagement
from core.logger import setup_logger

class AurusSingularis:
    """市場トレンド分析と適応戦略設計を行うAI（ヒストリカルデータ利用版）"""

    def __init__(self):
        self.logger = setup_logger("AurusLogger", "/opt/airflow/logs/AurusLogger.log")

        self._configure_gpu()
        self.model = self._build_model()
        self.market_fetcher = MarketDataFetcher()

        data_array = self.market_fetcher.get_usdjpy_historical_data(interval="1h", period="1mo")
        if data_array is None:
            self.logger.warning("⚠️ データ取得失敗。ダミーデータで初期化します")
            data_array = np.random.normal(loc=100, scale=5, size=(100, 5))

        columns = ["Open", "High", "Low", "Close", "Volume"]
        historical_data = pd.DataFrame(data_array, columns=columns)
        self.risk_manager = RiskManagement(historical_data=historical_data)

    def _configure_gpu(self):
        gpus = tf.config.list_physical_devices('GPU')
        if gpus:
            try:
                for gpu in gpus:
                    tf.config.experimental.set_memory_growth(gpu, True)
            except RuntimeError as e:
                self.logger.error(f"GPU メモリ設定エラー: {e}")

    def _build_model(self):
        model = tf.keras.Sequential([
            tf.keras.layers.Input(shape=(12,)),
            tf.keras.layers.Dense(128, activation='relu'),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(1, activation='sigmoid')
        ])
        model.compile(optimizer='adam', loss='mse')
        return model

    def process(self, market_data):
        if not isinstance(market_data, dict):
            self.logger.warning("⚠️ market_dataがlistなどで渡されました。空辞書に置換します")
            market_data = {}

        processed_data = self._preprocess_data(market_data)
        prediction = self.model.predict(processed_data, verbose=0)
        decision = "HOLD"
        if prediction > 0.6:
            decision = "BUY"
        elif prediction < 0.4:
            decision = "SELL"

        self.logger.info(f"[Aurus] input: {market_data}, prediction: {float(prediction)}, decision: {decision}")
        return decision

    def _preprocess_data(self, market_data):
        return np.array([
            market_data.get("price", 0.0),
            market_data.get("volume", 0.0),
            market_data.get("sentiment", 0.0),
            market_data.get("trend_strength", 0.0),
            market_data.get("volatility", 0.0),
            market_data.get("order_block", 0.0),
            market_data.get("institutional_flow", 0.0),
            market_data.get("short_interest", 0.0),
            market_data.get("momentum", 0.0),
            market_data.get("trend_prediction", 0.0),
            market_data.get("liquidity_ratio", 0.0),
            1
        ]).reshape(1, -1)
