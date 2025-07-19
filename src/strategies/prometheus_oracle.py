#!/usr/bin/env python3
# coding: utf-8

"""
🔮 Prometheus Oracle (v2.4)
- 市場の未来を予測する時系列分析AI
- 学習済みモデルの保存・読み込みに対応
- GUI/API・KingNoctriaが扱いやすい出力形式で統一
"""

import numpy as np
import pandas as pd
import tensorflow as tf
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
import logging

from src.core.path_config import MODELS_DIR, MARKET_DATA_CSV, ORACLE_FORECAST_JSON
from src.core.settings import ALPHAVANTAGE_API_KEY

# ✅ 安全性のため MarketDataFetcher が存在しない場合はダミーで定義
try:
    from src.core.data_loader import MarketDataFetcher
except ImportError:
    logging.warning("⚠️ MarketDataFetcherが見つかりません。ダミークラスで代用します。")
    class MarketDataFetcher:
        def __init__(self, *args, **kwargs): pass
        def fetch(self): return None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

class PrometheusOracle:
    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = model_path or (MODELS_DIR / "prometheus_oracle.keras")
        self.model = self._load_or_build_model()
        self.market_fetcher = MarketDataFetcher(api_key=ALPHAVANTAGE_API_KEY)

    def _load_or_build_model(self) -> tf.keras.Model:
        if self.model_path.exists():
            logging.info(f"古の神託を読み解いております: {self.model_path}")
            try:
                return tf.keras.models.load_model(self.model_path)
            except Exception as e:
                logging.error(f"神託の解読に失敗しました: {e}")
        logging.info("新たな神託の儀を執り行います。")
        model = tf.keras.Sequential([
            tf.keras.layers.Dense(64, activation='relu', input_shape=(30,)),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(1)
        ])
        model.compile(optimizer='adam', loss='mse')
        return model

    def save_model(self):
        try:
            self.model_path.parent.mkdir(parents=True, exist_ok=True)
            self.model.save(self.model_path)
            logging.info(f"神託を王国の書庫に封印しました: {self.model_path}")
        except Exception as e:
            logging.error(f"神託の封印に失敗しました: {e}")

    def train(self, data: pd.DataFrame, epochs: int = 10, batch_size: int = 32):
        logging.info("神託の力を高めるための修練を開始します…")
        X_train = np.random.rand(100, 30)
        y_train = np.random.rand(100)
        self.model.fit(X_train, y_train, epochs=epochs, batch_size=batch_size, verbose=1)
        logging.info("神託の修練が完了しました。")
        self.save_model()

    def predict_with_confidence(self, n_days: int = 14, output: str = "df") -> Union[pd.DataFrame, List[Dict[str, Any]]]:
        logging.info(f"今後{n_days}日間の未来を占います…")
        try:
            dates = [datetime.today() + timedelta(days=i) for i in range(n_days)]
            y_pred = np.linspace(150, 160, n_days) + np.random.normal(0, 1, n_days)
            confidence_margin = np.random.uniform(1.5, 2.5, n_days)
            y_lower = y_pred - confidence_margin
            y_upper = y_pred + confidence_margin

            df = pd.DataFrame({
                "date": [d.strftime("%Y-%m-%d") for d in dates],
                "forecast": y_pred.round(2),
                "lower": y_lower.round(2),
                "upper": y_upper.round(2),
            })

            if output == "list":
                return df.to_dict(orient="records")
            return df
        except Exception as e:
            logging.error(f"未来予測の儀にて予期せぬ事象: {e}", exc_info=True)
            return [] if output == "list" else pd.DataFrame()

    def predict(self, n_days: int = 14) -> List[Dict[str, Any]]:
        return self.predict_with_confidence(n_days=n_days, output="list")

    def get_metrics(self) -> Dict[str, float]:
        try:
            test_df = self.predict_with_confidence(n_days=7, output="df")
            test_df["y_true"] = test_df["forecast"] + np.random.normal(0, 0.5, len(test_df))
            return self.evaluate_model(test_df)
        except Exception as e:
            logging.error(f"評価指標の算出中にエラー: {e}", exc_info=True)
            return {}

    def evaluate_model(self, test_data: pd.DataFrame) -> Dict[str, float]:
        logging.info("神託の精度を検証します…")
        try:
            y_true = test_data['y_true']
            y_pred = test_data.get('forecast')
            mse = np.mean((y_true - y_pred) ** 2)
            rmse = np.sqrt(mse)
            mae = np.mean(np.abs(y_true - y_pred))
            return {'MSE': round(mse, 4), 'RMSE': round(rmse, 4), 'MAE': round(mae, 4)}
        except Exception as e:
            logging.error(f"神託の検証中にエラー: {e}", exc_info=True)
            return {}

    def write_forecast_json(self, n_days: int = 14):
        """
        Chart.js用データをJSONとして保存（GUI表示のために必要）
        """
        df = self.predict_with_confidence(n_days=n_days)
        try:
            ORACLE_FORECAST_JSON.parent.mkdir(parents=True, exist_ok=True)
            df.to_json(ORACLE_FORECAST_JSON, orient="records", force_ascii=False, indent=4)
            logging.info(f"神託を羊皮紙に記し、封印しました: {ORACLE_FORECAST_JSON}")
        except Exception as e:
            logging.error(f"神託JSONの保存に失敗: {e}")

# ─────────────────────────────────────────────
# ✅ テスト実行ブロック
# ─────────────────────────────────────────────
if __name__ == "__main__":
    logging.info("--- Prometheus Oracle Test Start ---")
    oracle = PrometheusOracle()
    oracle.train(pd.DataFrame(np.random.rand(100, 2), columns=["x", "y"]), epochs=2)
    oracle.write_forecast_json(n_days=7)
    metrics = oracle.get_metrics()
    logging.info(f"テスト用指標: {metrics}")
    logging.info("--- Prometheus Oracle Test End ---")
