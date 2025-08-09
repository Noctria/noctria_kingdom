#!/usr/bin/env python3
# coding: utf-8

"""
🔮 Prometheus Oracle (推論専用)
- 学習は train_prometheus.py に分離
- Plan層で生成した標準特徴量DataFrameから未来予測
"""

import numpy as np
import pandas as pd
import tensorflow as tf
from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path
import logging

from src.core.path_config import VERITAS_MODELS_DIR, ORACLE_FORECAST_JSON
from src.plan_data.standard_feature_schema import STANDARD_FEATURE_ORDER

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")


class PrometheusOracle:
    def __init__(
        self,
        model_path: Optional[Path] = None,
        feature_order: Optional[List[str]] = None,
    ):
        self.feature_order = feature_order or STANDARD_FEATURE_ORDER
        self.model_path = model_path or (VERITAS_MODELS_DIR / "prometheus_oracle.keras")
        self.model = self._load_model()

    def _load_model(self) -> tf.keras.Model:
        if self.model_path.exists():
            logging.info(f"神託モデル読込: {self.model_path}")
            try:
                return tf.keras.models.load_model(self.model_path)
            except Exception as e:
                logging.error(f"神託モデル読込失敗: {e}")
        raise FileNotFoundError(f"モデルが存在しません: {self.model_path}")

    def _align_and_clean(self, df: pd.DataFrame) -> pd.DataFrame:
        work = df.copy()

        for col in self.feature_order:
            if col not in work.columns:
                work[col] = 0.0

        work[self.feature_order] = work[self.feature_order].apply(
            pd.to_numeric, errors="coerce"
        ).ffill().bfill()

        work[self.feature_order] = work[self.feature_order].replace(
            [np.inf, -np.inf], np.nan
        ).fillna(0.0).astype(np.float32)

        return work[self.feature_order]

    def predict_future(
        self,
        features_df: pd.DataFrame,
        n_days: int = 14,
        decision_id: Optional[str] = None,
        caller: Optional[str] = "king_noctria",
        reason: Optional[str] = None,
    ) -> pd.DataFrame:
        clean = self._align_and_clean(features_df)
        n = min(n_days, len(clean))

        if n == 0:
            logging.warning("predict_future: 入力行が0のためダミー行を返します。")
            return pd.DataFrame({
                "date": [str(datetime.today())[:10]],
                "forecast": [np.nan],
                "lower": [np.nan],
                "upper": [np.nan],
                "decision_id": [decision_id],
                "caller": [caller],
                "reason": [reason],
            })

        df_input = clean.tail(n)
        y_pred = self.model.predict(df_input.values, verbose=0).astype(np.float32).flatten()

        if len(y_pred) > 1 and not np.allclose(np.std(y_pred), 0.0):
            confidence_margin = float(np.std(y_pred) * 1.5)
        else:
            confidence_margin = 2.0

        y_lower = y_pred - confidence_margin
        y_upper = y_pred + confidence_margin

        if "date" in features_df.columns:
            dates = pd.to_datetime(features_df["date"]).dt.strftime("%Y-%m-%d").tail(n).tolist()
        elif "Date" in features_df.columns:
            dates = pd.to_datetime(features_df["Date"]).dt.strftime("%Y-%m-%d").tail(n).tolist()
        else:
            dates = [(datetime.today() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(n)]

        return pd.DataFrame({
            "date": dates,
            "forecast": np.round(y_pred, 4),
            "lower": np.round(y_lower, 4),
            "upper": np.round(y_upper, 4),
            "decision_id": decision_id,
            "caller": caller,
            "reason": reason,
        })

    def write_forecast_json(
        self,
        features_df: pd.DataFrame,
        n_days: int = 14,
        decision_id: Optional[str] = None,
        caller: Optional[str] = "king_noctria",
        reason: Optional[str] = None,
    ):
        df = self.predict_future(features_df, n_days, decision_id, caller, reason)
        try:
            ORACLE_FORECAST_JSON.parent.mkdir(parents=True, exist_ok=True)
            df.to_json(ORACLE_FORECAST_JSON, orient="records", force_ascii=False, indent=4)
            logging.info(f"予測結果保存: {ORACLE_FORECAST_JSON}")
        except Exception as e:
            logging.error(f"予測JSON保存失敗: {e}")
