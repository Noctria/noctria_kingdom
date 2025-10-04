#!/usr/bin/env python3
# coding: utf-8
from __future__ import annotations

"""
Quick smoke test for PrometheusOracle with flexible backend options.

Usage examples:
  # Auto-detect
  python3 -m src.scripts.try_prometheus_oracle

  # Force Keras backend with your model path
  python3 -m src.scripts.try_prometheus_oracle --backend keras --model-path /path/to/model.keras

  # Make a dummy Keras model that matches STANDARD_FEATURE_ORDER width and test predict_future
  python3 -m src.scripts.try_prometheus_oracle --backend keras --make-dummy-keras --write-json

  # SB3 explicitly (requires stable-baselines3 & gymnasium)
  python3 -m src.scripts.try_prometheus_oracle --backend sb3 --model-path /path/to/model.zip
"""

import argparse
import logging
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd

from src.core.path_config import (
    ensure_import_path,
    ORACLE_FORECAST_JSON,
    DATA_DIR,
)

ensure_import_path()

from src.strategies.prometheus_oracle import PrometheusOracle
from src.plan_data.standard_feature_schema import STANDARD_FEATURE_ORDER

log = logging.getLogger("noctria.scripts.try_prometheus_oracle")
if not log.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")


def _make_dummy_features(n_rows: int = 120) -> pd.DataFrame:
    today = datetime.today()
    dates = [today - timedelta(days=i) for i in range(n_rows)]
    dates = list(reversed(dates))

    base = 150.0
    noise = np.random.normal(0, 1.2, n_rows).cumsum()
    close = base + noise
    volume = np.random.randint(100, 500, n_rows).astype(float)
    spread = np.random.uniform(0.005, 0.02, n_rows).astype(float)
    volatility = pd.Series(close).pct_change().rolling(20).std().fillna(0.0).values

    return pd.DataFrame(
        {
            "date": [d.strftime("%Y-%m-%d") for d in dates],
            "close": close,
            "volume": volume,
            "spread": spread,
            "volatility": volatility,
        }
    )


def _ensure_dummy_keras_model(output_path: Path, input_dim: int) -> Optional[Path]:
    """
    Create a tiny Keras model if TensorFlow is available.
    Returns path if created successfully, else None.
    """
    try:
        os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
        from tensorflow import keras  # type: ignore
        from tensorflow.keras import layers  # type: ignore

        model = keras.Sequential(
            [
                layers.Input(shape=(input_dim,)),
                layers.Dense(16, activation="relu"),
                layers.Dense(8, activation="relu"),
                layers.Dense(1, activation="linear"),
            ]
        )
        model.compile(optimizer="adam", loss="mse")

        # quick dummy training so the model is usable
        X = np.random.randn(512, input_dim).astype("float32")
        y = (X.sum(axis=1, keepdims=True) + np.random.randn(512, 1) * 0.1).astype("float32")
        model.fit(X, y, epochs=2, verbose=0)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        model.save(output_path)
        log.info("Dummy Keras model created -> %s (input_dim=%d)", output_path, input_dim)
        return output_path
    except Exception as e:
        log.warning("Failed to create dummy Keras model: %s", e)
        return None


def main():
    ap = argparse.ArgumentParser(description="Smoke test for PrometheusOracle")
    ap.add_argument("--rows", type=int, default=120, help="Feature rows to synthesize")
    ap.add_argument("--n-days", type=int, default=14, help="Days to forecast for predict_future")
    ap.add_argument("--deterministic", action="store_true", help="SB3 deterministic prediction")
    ap.add_argument(
        "--write-json", action="store_true", help=f"Write forecast JSON to {ORACLE_FORECAST_JSON}"
    )
    ap.add_argument(
        "--backend",
        choices=["auto", "keras", "sb3"],
        default="auto",
        help="Force backend. 'auto' keeps PrometheusOracle auto-detection.",
    )
    ap.add_argument(
        "--model-path",
        type=str,
        default="",
        help="Path to model (.keras/.h5/dir for Keras, .zip for SB3)",
    )
    ap.add_argument(
        "--make-dummy-keras", action="store_true", help="Create a tiny Keras model if none given"
    )
    ap.add_argument(
        "--input-dim",
        type=int,
        default=0,
        help="Override input dim for dummy Keras (0=auto based on STANDARD_FEATURE_ORDER)",
    )
    args = ap.parse_args()

    # Prepare dummy features
    features = _make_dummy_features(args.rows)

    model_path: Optional[Path] = Path(args.model_path).resolve() if args.model_path else None

    # Determine expected input width for Keras from feature schema
    auto_input_dim = len(STANDARD_FEATURE_ORDER)

    # If user forced keras but didn't provide a model, optionally make a dummy one
    if args.backend == "keras" and model_path is None and args.make_dummy_keras:
        input_dim = args.input - dim if args.input_dim > 0 else auto_input_dim
        default_dummy = Path(DATA_DIR) / "models" / "prometheus_oracle_dummy.keras"
        model_path = _ensure_dummy_keras_model(default_dummy, input_dim=input_dim)

    # Instantiate oracle
    if args.backend == "auto":
        oracle = PrometheusOracle(lazy=True, deterministic=args.deterministic, model_path=None)
    else:
        oracle = PrometheusOracle(
            lazy=True, deterministic=args.deterministic, model_path=model_path or ""
        )

    log.info("=== PrometheusOracle status (before) ===")
    log.info(oracle.status())

    # ---- Keras-style forecast API ----
    if args.backend in ("auto", "keras"):
        log.info("=== predict_future (Keras backend only; otherwise returns a safe dummy row) ===")
        forecast_df = oracle.predict_future(
            features_df=features,
            n_days=args.n_days,
            decision_id="TEST-PROM-FORECAST",
            caller="smoke_test",
            reason=f"try_prometheus_oracle backend={args.backend}",
        )
        print("\n[forecast tail]")
        print(forecast_df.tail(min(5, len(forecast_df))))
        if args.write_json:
            try:
                ORACLE_FORECAST_JSON.parent.mkdir(parents=True, exist_ok=True)
                forecast_df.to_json(
                    ORACLE_FORECAST_JSON, orient="records", force_ascii=False, indent=2
                )
                log.info("wrote forecast JSON -> %s", ORACLE_FORECAST_JSON)
            except Exception as e:
                log.warning("failed to write forecast JSON: %s", e)

    # ---- SB3-style decision API ----
    if args.backend in ("auto", "sb3"):
        log.info("=== decide (SB3; returns HOLD safely if not sb3 or on any mismatch) ===")
        signal = oracle.decide()
        print(f"\n[decision] {signal}")

    log.info("=== PrometheusOracle status (after) ===")
    log.info(oracle.status())


if __name__ == "__main__":
    main()
