#!/usr/bin/env python3
# coding: utf-8

"""
🔮 Prometheus Oracle (標準feature_order準拠)
- Plan層（features/analyzer等）で生成した標準特徴量DataFrameから未来予測
- feature_orderはPlan層設計で標準化・連携
"""

import numpy as np
import pandas as pd
import tensorflow as tf
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path
import logging

from src.core.path_config import VERITAS_MODELS_DIR, ORACLE_FORECAST_JSON
from src.plan_data.standard_feature_schema import STANDARD_FEATURE_ORDER

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

class PrometheusOracle:
    def __init__(
        self,
        model_path: Optional[Path] = None,
        feature_order: Optional[List[str]] = None
    ):
        self.feature_order = feature_order or STANDARD_FEATURE_ORDER
        self.model_path = model_path or (VERITAS_MODELS_DIR / "prometheus_oracle.keras")
        self.model = self._load_or_build_model(input_dim=len(self.feature_order))

    def _load_or_build_model(self, input_dim: int) -> tf.keras.Model:
        if self.model_path.exists():
            logging.info(f"神託モデル読込: {self.model_path}")
            try:
                return tf.keras.models.load_model(self.model_path)
            except Exception as e:
                logging.error(f"神託モデル読込失敗: {e}")
        logging.info(f"新規神託モデル構築 (input_dim={input_dim})")
        model = tf.keras.Sequential([
            tf.keras.layers.Dense(64, activation='relu', input_shape=(input_dim,)),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(1)
        ])
        model.compile(optimizer='adam', loss='mse')
        return model

    def save_model(self):
        try:
            self.model_path.parent.mkdir(parents=True, exist_ok=True)
            self.model.save(self.model_path)
            logging.info(f"神託モデル保存: {self.model_path}")
        except Exception as e:
            logging.error(f"神託モデル保存失敗: {e}")

    def train(
        self,
        features_df: pd.DataFrame,
        target_col: str,
        epochs: int = 10,
        batch_size: int = 32
    ):
        X_train = features_df[self.feature_order].values
        y_train = features_df[target_col].values
        self.model = self._load_or_build_model(input_dim=len(self.feature_order))
        self.model.fit(X_train, y_train, epochs=epochs, batch_size=batch_size, verbose=1)
        self.save_model()

    def predict_future(
        self,
        features_df: pd.DataFrame,
        n_days: int = 14,
        decision_id: Optional[str] = None,
        caller: Optional[str] = "king_noctria",
        reason: Optional[str] = None
    ) -> pd.DataFrame:
        df_input = features_df[self.feature_order].tail(n_days)
        X_input = df_input.values
        y_pred = self.model.predict(X_input).flatten()
        confidence_margin = np.std(y_pred) * 1.5 if len(y_pred) > 1 else 2.0
        y_lower = y_pred - confidence_margin
        y_upper = y_pred + confidence_margin

        if 'Date' in features_df.columns:
            dates = features_df['Date'].tail(n_days).tolist()
        else:
            dates = [str(datetime.today() + timedelta(days=i))[:10] for i in range(n_days)]

        df = pd.DataFrame({
            "date": dates,
            "forecast": y_pred.round(4),
            "lower": y_lower.round(4),
            "upper": y_upper.round(4),
            "decision_id": decision_id,
            "caller": caller,
            "reason": reason
        })
        return df

    def write_forecast_json(
        self,
        features_df: pd.DataFrame,
        n_days: int = 14,
        decision_id: Optional[str] = None,
        caller: Optional[str] = "king_noctria",
        reason: Optional[str] = None
    ):
        df = self.predict_future(features_df, n_days, decision_id, caller, reason)
        try:
            ORACLE_FORECAST_JSON.parent.mkdir(parents=True, exist_ok=True)
            df.to_json(ORACLE_FORECAST_JSON, orient="records", force_ascii=False, indent=4)
            logging.info(f"予測結果保存: {ORACLE_FORECAST_JSON}")
        except Exception as e:
            logging.error(f"予測JSON保存失敗: {e}")

# === テスト例 ===
if __name__ == "__main__":
    logging.info("--- Prometheus Oracle feature_orderテスト ---")
    test_df = pd.DataFrame(
        np.random.rand(30, len(STANDARD_FEATURE_ORDER)),
        columns=STANDARD_FEATURE_ORDER
    )
    test_df['target'] = test_df[STANDARD_FEATURE_ORDER[0]].shift(-1).fillna(method='ffill')
    oracle = PrometheusOracle(feature_order=STANDARD_FEATURE_ORDER)
    oracle.train(test_df, target_col="target", epochs=2)
    forecast_df = oracle.predict_future(test_df, n_days=5, decision_id="KC-TEST", caller="test", reason="unit_test")
    print(forecast_df.tail(5))
    oracle.write_forecast_json(test_df, n_days=5, decision_id="KC-TEST", caller="test", reason="unit_test")
    logging.info("--- Prometheus Oracle feature_orderテスト完了 ---")
