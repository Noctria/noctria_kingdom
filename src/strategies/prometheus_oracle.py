# src/strategies/prometheus_oracle.py

import numpy as np
import pandas as pd
import tensorflow as tf
from datetime import datetime, timedelta
from core.data_loader import MarketDataFetcher
from core.settings import ALPHAVANTAGE_API_KEY
from pathlib import Path


class PrometheusOracle:
    def __init__(self):
        self.model = self._build_model()
        self.market_fetcher = MarketDataFetcher(api_key=ALPHAVANTAGE_API_KEY)

    def _build_model(self):
        model = tf.keras.Sequential([
            tf.keras.layers.Dense(64, activation='relu', input_shape=(30,)),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(1)
        ])
        model.compile(optimizer='adam', loss='mse')
        return model

    def predict(self, n_days: int = 30) -> pd.DataFrame:
        # ダミーデータで予測（本来は学習・推論済みモデルを使用）
        dates = [datetime.today() + timedelta(days=i) for i in range(n_days)]
        y_pred = np.linspace(150, 160, n_days) + np.random.normal(0, 1, n_days)
        y_lower = y_pred - np.random.uniform(1, 2, n_days)
        y_upper = y_pred + np.random.uniform(1, 2, n_days)
        return pd.DataFrame({
            "date": [d.strftime("%Y-%m-%d") for d in dates],
            "y_pred": y_pred.round(2),
            "y_lower": y_lower.round(2),
            "y_upper": y_upper.round(2),
        })

# ✅ GUIから呼び出し用
def predict_and_save(output_path: Path, n_days: int = 30):
    oracle = PrometheusOracle()
    df = oracle.predict(n_days=n_days)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_json(output_path, orient="records", force_ascii=False)
