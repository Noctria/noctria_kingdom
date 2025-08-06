#!/usr/bin/env python3
# coding: utf-8

"""
🔮 Prometheus Oracle (Plan層連携バージョン)
- Plan層（features/analyzer等）で生成した特徴量DataFrameから未来予測
- 予測にはdecision_id/caller/reasonを記録返却
- モデル訓練もDataFrame直受け（feature_order指定）
"""

import numpy as np
import pandas as pd
import tensorflow as tf
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
import logging

from src.core.path_config import VERITAS_MODELS_DIR, ORACLE_FORECAST_JSON

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

class PrometheusOracle:
    def __init__(
        self,
        model_path: Optional[Path] = None,
        feature_order: Optional[List[str]] = None,
    ):
        self.model_path = model_path or (VERITAS_MODELS_DIR / "prometheus_oracle.keras")
        self.feature_order = feature_order  # List[str], Plan層で定義した特徴量カラム順
        self.model = self._load_or_build_model(input_dim=len(feature_order) if feature_order else 30)

    def _load_or_build_model(self, input_dim: int = 30) -> tf.keras.Model:
        if self.model_path.exists():
            logging.info(f"古の神託を読み解いております: {self.model_path}")
            try:
                return tf.keras.models.load_model(self.model_path)
            except Exception as e:
                logging.error(f"神託の解読に失敗しました: {e}")
        logging.info("新たな神託の儀を執り行います。")
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
            logging.info(f"神託を王国の書庫に封印しました: {self.model_path}")
        except Exception as e:
            logging.error(f"神託の封印に失敗しました: {e}")

    def train(
        self,
        features_df: pd.DataFrame,
        target_col: str,
        epochs: int = 10,
        batch_size: int = 32
    ):
        if not self.feature_order:
            raise ValueError("feature_order（特徴量カラム順）を指定してください。")
        X_train = features_df[self.feature_order].values
        y_train = features_df[target_col].values
        self.model.fit(X_train, y_train, epochs=epochs, batch_size=batch_size, verbose=1)
        logging.info("神託の修練が完了しました。")
        self.save_model()

    def predict_future(
        self,
        features_df: pd.DataFrame,
        n_days: int = 14,
        decision_id: Optional[str] = None,
        caller: Optional[str] = "king_noctria",
        reason: Optional[str] = None
    ) -> pd.DataFrame:
        if not self.feature_order:
            raise ValueError("feature_order（特徴量カラム順）を指定してください。")
        # 直近n日分の特徴量で未来予測
        df_input = features_df[self.feature_order].tail(n_days)
        X_input = df_input.values
        y_pred = self.model.predict(X_input).flatten()
        # ここで信頼区間などを計算・追加も可能
        confidence_margin = np.std(y_pred) * 1.5 if len(y_pred) > 1 else 2.0
        y_lower = y_pred - confidence_margin
        y_upper = y_pred + confidence_margin

        # 日付
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
            logging.info(f"神託を羊皮紙に記し、封印しました: {ORACLE_FORECAST_JSON}")
        except Exception as e:
            logging.error(f"神託JSONの保存に失敗: {e}")

# =====================
# ✅ テストブロック
# =====================
if __name__ == "__main__":
    logging.info("--- Prometheus Oracle Plan連携テスト ---")
    # ▼ 例: Plan層から特徴量DataFrameを生成
    plan_features = pd.DataFrame(
        np.random.rand(30, 8),  # 8特徴量・30サンプル
        columns=["USDJPY_Close", "USDJPY_Volatility_5d", "SP500_Close", "VIX_Close",
                 "News_Count", "CPIAUCSL_Value", "FEDFUNDS_Value", "UNRATE_Value"]
    )
    # ▼ feature_orderはPlan層設計と一致させる
    feature_order = [
        "USDJPY_Close", "USDJPY_Volatility_5d", "SP500_Close", "VIX_Close",
        "News_Count", "CPIAUCSL_Value", "FEDFUNDS_Value", "UNRATE_Value"
    ]
    plan_features['target'] = plan_features["USDJPY_Close"].shift(-1).fillna(method='ffill')
    oracle = PrometheusOracle(feature_order=feature_order)
    oracle.train(plan_features, target_col="target", epochs=3)
    forecast_df = oracle.predict_future(plan_features, n_days=7, decision_id="KC-TEST", caller="test", reason="単体テスト")
    print(forecast_df.tail(7))
    oracle.write_forecast_json(plan_features, n_days=7, decision_id="KC-TEST", caller="test", reason="単体テスト")
    logging.info("--- Prometheus Oracle Plan連携テスト完了 ---")
