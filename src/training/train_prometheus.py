#!/usr/bin/env python3
# coding: utf-8

"""
🏋️‍♂️ Prometheus Oracle 学習スクリプト
- 過去特徴量データとターゲットを読み込み学習
- 学習済みモデルを保存
"""

import numpy as np
import pandas as pd
import tensorflow as tf
import logging
from pathlib import Path
from typing import Optional, List

from src.core.path_config import VERITAS_MODELS_DIR
from src.plan_data.standard_feature_schema import STANDARD_FEATURE_ORDER
from src.strategies.prometheus_oracle import PrometheusOracle

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")


def build_model(input_dim: int) -> tf.keras.Model:
    inputs = tf.keras.Input(shape=(input_dim,), dtype=tf.float32, name="features")
    x = tf.keras.layers.Dense(64, activation="relu")(inputs)
    x = tf.keras.layers.Dense(32, activation="relu")(x)
    outputs = tf.keras.layers.Dense(1, name="yhat")(x)
    model = tf.keras.Model(inputs=inputs, outputs=outputs, name="prometheus_oracle")
    model.compile(optimizer="adam", loss="mse")
    return model


def train_prometheus(
    features_df: pd.DataFrame,
    target_col: str,
    epochs: int = 10,
    batch_size: int = 32,
    model_path: Optional[Path] = None,
    feature_order: Optional[List[str]] = None,
):
    oracle = PrometheusOracle(model_path=model_path, feature_order=feature_order or STANDARD_FEATURE_ORDER)

    # モデルは再構築（学習時は常に新規）
    model = build_model(input_dim=len(oracle.feature_order))

    X = oracle._align_and_clean(features_df).values
    y = pd.to_numeric(features_df[target_col], errors="coerce").ffill().bfill()
    y = y.replace([np.inf, -np.inf], np.nan).fillna(0.0).astype(np.float32).values

    model.fit(X, y, epochs=epochs, batch_size=batch_size, verbose=1)

    save_path = model_path or (VERITAS_MODELS_DIR / "prometheus_oracle.keras")
    save_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(save_path)
    logging.info(f"学習済みモデル保存: {save_path}")


if __name__ == "__main__":
    # === テスト用のダミーデータ ===
    rng = np.random.RandomState(0)
    dummy_df = pd.DataFrame(rng.rand(100, len(STANDARD_FEATURE_ORDER)), columns=STANDARD_FEATURE_ORDER)
    dummy_df["target"] = dummy_df[STANDARD_FEATURE_ORDER[0]].shift(-1).fillna(0.0)

    train_prometheus(dummy_df, target_col="target", epochs=2, batch_size=8)
