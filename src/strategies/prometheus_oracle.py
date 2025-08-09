#!/usr/bin/env python3
# coding: utf-8

"""
🔮 Prometheus Oracle (標準feature_order準拠)
- Plan層で生成した標準特徴量DataFrameから未来予測
- feature_order は Plan 層設計で標準化・連携
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
        self.model = self._load_or_build_model(input_dim=len(self.feature_order))

    # -------------------- Model I/O --------------------
    def _load_or_build_model(self, input_dim: int) -> tf.keras.Model:
        if self.model_path.exists():
            logging.info(f"神託モデル読込: {self.model_path}")
            try:
                return tf.keras.models.load_model(self.model_path)
            except Exception as e:
                logging.error(f"神託モデル読込失敗: {e}")

        logging.info(f"新規神託モデル構築 (input_dim={input_dim})")
        inputs = tf.keras.Input(shape=(input_dim,), dtype=tf.float32, name="features")
        x = tf.keras.layers.Dense(64, activation="relu")(inputs)
        x = tf.keras.layers.Dense(32, activation="relu")(x)
        outputs = tf.keras.layers.Dense(1, name="yhat")(x)
        model = tf.keras.Model(inputs=inputs, outputs=outputs, name="prometheus_oracle")
        model.compile(optimizer="adam", loss="mse")
        return model

    def save_model(self):
        try:
            self.model_path.parent.mkdir(parents=True, exist_ok=True)
            self.model.save(self.model_path)
            logging.info(f"神託モデル保存: {self.model_path}")
        except Exception as e:
            logging.error(f"神託モデル保存失敗: {e}")

    # -------------------- Data prep --------------------
    def _align_and_clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        - feature_order に合わせて列を並べる/不足列は 0.0 で新設
        - 数値化（非数値は NaN）
        - ffill/bfill で連続埋め
        - 残る NaN / inf / -inf は 0.0 に置換
        """
        work = df.copy()

        # 必要列の確保（不足列は 0.0）
        for col in self.feature_order:
            if col not in work.columns:
                work[col] = 0.0

        # 数値化
        work[self.feature_order] = work[self.feature_order].apply(
            pd.to_numeric, errors="coerce"
        )

        # 連続埋め（前→後）
        work[self.feature_order] = work[self.feature_order].ffill().bfill()

        # 残 NaN/inf を 0.0
        work[self.feature_order] = work[self.feature_order].replace(
            [np.inf, -np.inf], np.nan
        ).fillna(0.0)

        # 型は float32 に寄せる（TF と相性良）
        work[self.feature_order] = work[self.feature_order].astype(np.float32)

        # デバッグ: NaN チェック
        nan_counts = work[self.feature_order].isna().sum().sum()
        if nan_counts:
            logging.warning(f"前処理後にも NaN が {nan_counts} 個残存 → 0.0 置換済み")

        return work[self.feature_order]

    # -------------------- Train / Predict --------------------
    def train(
        self,
        features_df: pd.DataFrame,
        target_col: str,
        epochs: int = 10,
        batch_size: int = 32,
    ):
        X = self._align_and_clean(features_df).values
        y = pd.to_numeric(features_df[target_col], errors="coerce").ffill().bfill()
        y = y.replace([np.inf, -np.inf], np.nan).fillna(0.0).astype(np.float32).values

        self.model = self._load_or_build_model(input_dim=len(self.feature_order))
        self.model.fit(X, y, epochs=epochs, batch_size=batch_size, verbose=1)
        self.save_model()

    def predict_future(
        self,
        features_df: pd.DataFrame,
        n_days: int = 14,
        decision_id: Optional[str] = None,
        caller: Optional[str] = "king_noctria",
        reason: Optional[str] = None,
    ) -> pd.DataFrame:
        # 安全な前処理
        clean = self._align_and_clean(features_df)

        # 行数が足りない場合はある分だけ
        n = min(n_days, len(clean))
        if n == 0:
            # 何もない場合はダミー 1 行返す
            logging.warning("predict_future: 入力行が 0 のためダミー行を返します。")
            dates = [str(datetime.today())[:10]]
            return pd.DataFrame(
                {
                    "date": dates,
                    "forecast": [np.nan],
                    "lower": [np.nan],
                    "upper": [np.nan],
                    "decision_id": [decision_id],
                    "caller": [caller],
                    "reason": [reason],
                }
            )

        df_input = clean.tail(n)
        X_input = df_input.values

        # 推論
        y_pred = self.model.predict(X_input, verbose=0).astype(np.float32).flatten()

        # 信頼幅（単純な分散ベース）
        if len(y_pred) > 1 and not np.allclose(np.std(y_pred), 0.0):
            confidence_margin = float(np.std(y_pred) * 1.5)
        else:
            confidence_margin = 2.0

        y_lower = y_pred - confidence_margin
        y_upper = y_pred + confidence_margin

        # 日付列：あれば 'date' を優先、無ければ今日からの連番
        if "date" in features_df.columns:
            dates = pd.to_datetime(features_df["date"]).dt.strftime("%Y-%m-%d").tail(n).tolist()
        elif "Date" in features_df.columns:
            dates = pd.to_datetime(features_df["Date"]).dt.strftime("%Y-%m-%d").tail(n).tolist()
        else:
            dates = [(datetime.today() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(n)]

        out = pd.DataFrame(
            {
                "date": dates,
                "forecast": np.round(y_pred, 4),
                "lower": np.round(y_lower, 4),
                "upper": np.round(y_upper, 4),
                "decision_id": decision_id,
                "caller": caller,
                "reason": reason,
            }
        )
        return out

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


# === テスト例 ===
if __name__ == "__main__":
    logging.info("--- Prometheus Oracle feature_orderテスト ---")
    # 疑似データ（NaN を混ぜて堅牢性チェック）
    rng = np.random.RandomState(0)
    test_df = pd.DataFrame(rng.rand(30, len(STANDARD_FEATURE_ORDER)), columns=STANDARD_FEATURE_ORDER)
    test_df.loc[5:7, STANDARD_FEATURE_ORDER[0]] = np.nan
    test_df["target"] = test_df[STANDARD_FEATURE_ORDER[0]].shift(-1)

    oracle = PrometheusOracle(feature_order=STANDARD_FEATURE_ORDER)
    oracle.train(test_df, target_col="target", epochs=2, batch_size=8)
    forecast_df = oracle.predict_future(test_df, n_days=5, decision_id="KC-TEST", caller="test", reason="unit_test")
    print(forecast_df.tail(5))
    oracle.write_forecast_json(test_df, n_days=5, decision_id="KC-TEST", caller="test", reason="unit_test")
    logging.info("--- Prometheus Oracle feature_orderテスト完了 ---")
