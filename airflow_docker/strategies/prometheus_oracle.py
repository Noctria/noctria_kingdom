# airflow_docker/strategies/prometheus_oracle.py

import numpy as np
import pandas as pd
import tensorflow as tf
from datetime import datetime, timedelta

from data.market_data_fetcher import MarketDataFetcher
from core.risk_managemer import RiskManager
from core.logger import setup_logger


class PrometheusOracle:
    """🔮 市場予測を行うAI（ヒストリカルデータ利用版・MetaAI改修版）"""

    def __init__(self):
        self.logger = setup_logger("PrometheusLogger")
        self.model = self._build_model()
        self.market_fetcher = MarketDataFetcher()

        data_array = self.market_fetcher.get_usdjpy_historical_data(interval="1h", period="1mo")
        if data_array is None:
            self.logger.warning("⚠️ データ取得失敗。ダミーデータで初期化します")
            data_array = np.random.normal(loc=100, scale=5, size=(100, 5))

        columns = ["Open", "High", "Low", "Close", "Volume"]
        historical_data = pd.DataFrame(data_array, columns=columns)

        # ✅ 正しいクラス名
        self.risk_manager = RiskManager(historical_data=historical_data)

    def _build_model(self):
        model = tf.keras.Sequential([
            tf.keras.layers.Dense(128, activation='relu', input_shape=(12,)),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(1, activation='linear')
        ])
        model.compile(optimizer='adam', loss='mse')
        return model

    def _preprocess_data(self, market_data):
        if not isinstance(market_data, dict):
            self.logger.warning("⚠️ market_dataがlistなどで渡されたため空辞書に置換")
            market_data = {}

        return np.array([[
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
            1.0  # バイアス項
        ]])

    def predict_market(self, market_data):
        processed_data = self._preprocess_data(market_data)
        prediction = self.model.predict(processed_data, verbose=0)
        self.logger.info(f"📈 Prometheus予測: 入力 = {market_data}, 出力 = {prediction[0][0]:.4f}")
        return float(prediction[0][0])

    def predict(self, days: int = 7):
        """📈 GUI向け：未来日付の時系列予測（Chart.js用）"""
        forecast = []
        today = datetime.today()
        for i in range(days):
            date = (today + timedelta(days=i)).strftime("%Y-%m-%d")
            mock_data = {
                "price": 100 + np.random.randn(),
                "volume": 1000,
                "volatility": np.random.rand(),
                "trend_prediction": 0.6 + 0.1 * np.sin(i),
            }
            y_pred = self.predict_market(mock_data)
            forecast.append({
                "date": date,
                "forecast": round(y_pred, 2),
                "lower": round(y_pred - 2.5, 2),
                "upper": round(y_pred + 2.5, 2),
            })
        return forecast

    def get_metrics(self):
        """📊 評価メトリクスのダミー値を返す"""
        return {
            "RMSE": round(np.random.uniform(0.5, 1.5), 4),
            "MAE": round(np.random.uniform(0.3, 1.0), 4),
            "MAPE": round(np.random.uniform(1.0, 5.0), 2)
        }


# ✅ テスト用ブロック
if __name__ == "__main__":
    oracle = PrometheusOracle()
    result = oracle.predict()
    print("🔮 Oracle予測:", result)
    print("📊 メトリクス:", oracle.get_metrics())
