#!/usr/bin/env python3
# coding: utf-8

"""
🔮 Prometheus Oracle (推論専用 / 二刀流)
- Keras モデル(.keras/.h5/SavedModel): DataFrame からの将来予測 (predict_future)
- SB3 モデル(.zip): 環境1ステップの推論で売買シグナル (decide)
"""

from __future__ import annotations

import json
import logging
import os
from importlib import import_module
from pathlib import Path
from typing import Optional, List, Any, Dict, Tuple

import numpy as np
import pandas as pd

# Optional deps
try:
    import tensorflow as tf  # type: ignore
except Exception:
    tf = None  # type: ignore

try:
    from stable_baselines3 import PPO  # type: ignore
except Exception:
    PPO = None  # type: ignore

try:
    import gymnasium as gym  # type: ignore
except Exception:
    gym = None  # type: ignore

from datetime import datetime, timedelta

from src.core.path_config import VERITAS_MODELS_DIR, ORACLE_FORECAST_JSON
from src.plan_data.standard_feature_schema import STANDARD_FEATURE_ORDER

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")


def _import_from_module_class(spec: str):
    """
    "pkg.mod:ClassName" を import して Class を返す。
    例: "src.envs.noctria_fx_trading_env:NoctriaFXTradingEnv"
    """
    if ":" not in spec:
        raise ValueError(f"Invalid module:Class spec: {spec}")
    mod, cls = spec.split(":", 1)
    m = import_module(mod)
    return getattr(m, cls)


class PrometheusOracle:
    """
    - Keras: DataFrame → 連続値予測（既存仕様）
    - SB3  : env 1ステップ推論 → "BUY"/"SELL"/"HOLD"
    """

    def __init__(
        self,
        model_path: Optional[Path | str] = None,
        feature_order: Optional[List[str]] = None,
    ):
        self.feature_order = feature_order or STANDARD_FEATURE_ORDER
        default_path = VERITAS_MODELS_DIR / "prometheus_oracle.keras"
        self.model_path: Path = Path(model_path) if model_path else default_path  # ← strでもOK
        self.backend: str = ""  # "keras" | "sb3"
        self.model: Any = self._load_model(self.model_path)

    # ---------- Loaders ----------
    def _load_model(self, p: Path) -> Any:
        if not p.exists():
            raise FileNotFoundError(f"モデルが存在しません: {p}")

        suffix = p.suffix.lower()

        # SB3 (.zip)
        if suffix == ".zip":
            if PPO is None:
                raise RuntimeError("stable-baselines3 が見つかりません（SB3モデル読込に必要）")
            log.info("神託モデル読込(SB3): %s", p)
            try:
                # device は CPU 固定（推論のみ）
                model = PPO.load(str(p), device="cpu")
            except Exception as e:
                log.error("SB3モデル読込失敗: %s", e)
                raise
            self.backend = "sb3"
            return model

        # それ以外は Keras 想定（.keras/.h5/ディレクトリSavedModelなど）
        if tf is None:
            raise RuntimeError("TensorFlow が見つかりません（Kerasモデル読込に必要）")
        log.info("神託モデル読込(Keras): %s", p)
        try:
            model = tf.keras.models.load_model(p)
        except Exception as e:
            log.error("Kerasモデル読込失敗: %s", e)
            raise
        self.backend = "keras"
        return model

    # ---------- Preprocess for Keras ----------
    def _align_and_clean(self, df: pd.DataFrame) -> pd.DataFrame:
        work = df.copy()

        for col in self.feature_order:
            if col not in work.columns:
                work[col] = 0.0

        work[self.feature_order] = (
            work[self.feature_order]
            .apply(pd.to_numeric, errors="coerce")
            .ffill()
            .bfill()
            .replace([np.inf, -np.inf], np.nan)
            .fillna(0.0)
            .astype(np.float32)
        )
        return work[self.feature_order]

    # ---------- Keras forecast API ----------
    def predict_future(
        self,
        features_df: pd.DataFrame,
        n_days: int = 14,
        decision_id: Optional[str] = None,
        caller: Optional[str] = "king_noctria",
        reason: Optional[str] = None,
    ) -> pd.DataFrame:
        if self.backend != "keras":
            log.warning("predict_future は Keras バックエンド専用です（現在: %s）。ダミーを返します。", self.backend)
            return pd.DataFrame({
                "date": [str(datetime.today())[:10]],
                "forecast": [np.nan],
                "lower": [np.nan],
                "upper": [np.nan],
                "decision_id": [decision_id],
                "caller": [caller],
                "reason": [f"backend={self.backend} is not keras"],
            })

        clean = self._align_and_clean(features_df)
        n = min(n_days, len(clean))

        if n == 0:
            log.warning("predict_future: 入力行が0のためダミー行を返します。")
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
            log.info("予測結果保存: %s", ORACLE_FORECAST_JSON)
        except Exception as e:
            log.error("予測JSON保存失敗: %s", e)

    # ---------- SB3 decision API ----------
    def decide(self) -> str:
        """
        "BUY" | "SELL" | "HOLD" を返す。
        - backend=sb3 のときのみ環境1ステップで推論
        - backend=keras のときは、ドメイン結線が未定のため安全に "HOLD"
        """
        if self.backend == "sb3":
            return self._decide_with_sb3()
        return "HOLD"

    def _decide_with_sb3(self) -> str:
        if gym is None:
            log.warning("gymnasium が無いため SB3 推論不可。HOLDを返します。")
            return "HOLD"

        # --- Env 構築 ---
        env_spec = os.environ.get("PROMETHEUS_ENV", "")
        env_kwargs_text = os.environ.get("PROMETHEUS_ENV_KWARGS", "{}")
        try:
            env_kwargs: Dict[str, Any] = json.loads(env_kwargs_text) if env_kwargs_text.strip() else {}
        except Exception:
            env_kwargs = {}
            log.warning("PROMETHEUS_ENV_KWARGS の JSON 解析に失敗。空dictを使用します。")

        try:
            if env_spec:
                EnvCls = _import_from_module_class(env_spec)
                env = EnvCls(**env_kwargs)
            else:
                env_id = os.environ.get("PROMETHEUS_GYM_ID", "CartPole-v1")
                env = gym.make(env_id, **env_kwargs)
        except Exception as e:
            log.warning("SB3環境初期化に失敗。HOLDを返します。理由: %s", e)
            return "HOLD"

        # --- 形状ガード（モデル観測次元 vs Env観測次元の突合）---
        try:
            model_obs_space = getattr(getattr(self.model, "policy", None), "observation_space", None) \
                              or getattr(self.model, "observation_space", None)
            obs_shape_model: Tuple[int, ...] = tuple(getattr(model_obs_space, "shape", ()) or ())
            obs_shape_env: Tuple[int, ...] = tuple(getattr(env.observation_space, "shape", ()) or ())

            if obs_shape_model and obs_shape_env and (obs_shape_model != obs_shape_env):
                log.warning(
                    "SB3 形状不一致につき HOLD: model_obs=%s, env_obs=%s. "
                    "学習時と同一のEnv / 特徴次元に揃えてください。",
                    obs_shape_model, obs_shape_env
                )
                try:
                    env.close()
                except Exception:
                    pass
                return "HOLD"
        except Exception as e:
            log.warning("SB3 形状ガード実行中に例外。安全のため HOLD: %s", e)
            try:
                env.close()
            except Exception:
                pass
            return "HOLD"

        # --- 推論 ---
        try:
            obs, _ = env.reset(seed=42)
            action, _ = self.model.predict(obs, deterministic=True)
        except Exception as e:
            log.warning("SB3推論に失敗。HOLDを返します。理由: %s", e)
            try:
                env.close()
            except Exception:
                pass
            return "HOLD"

        signal = self._map_action_to_signal(action, env)
        try:
            env.close()
        except Exception:
            pass
        return signal

    @staticmethod
    def _map_action_to_signal(action: Any, env: Any) -> str:
        """
        離散アクションの簡易マッピング：
          n=3 → {0: SELL, 1: HOLD, 2: BUY}
          n=2 → {0: SELL, 1: BUY}
        それ以外/連続は HOLD。
        """
        try:
            space = env.action_space
            if hasattr(space, "n"):
                n = int(space.n)
                a = int(action)
                if n == 3:
                    return {0: "SELL", 1: "HOLD", 2: "BUY"}.get(a, "HOLD")
                if n == 2:
                    return {0: "SELL", 1: "BUY"}.get(a, "HOLD")
        except Exception:
            pass
        return "HOLD"
