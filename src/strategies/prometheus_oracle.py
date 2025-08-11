#!/usr/bin/env python3
# coding: utf-8

"""
🔮 Prometheus Oracle (推論専用 / 二刀流)
- Keras (.keras/.h5/SavedModel): DataFrame からの将来予測 (predict_future)
- SB3   (.zip)                 : 環境1ステップの推論で売買シグナル (decide)

変更点:
- __init__ でモデルをロードしない（遅延ロード）
- 既定は SB3 の latest/model.zip を自動検出。無ければ Keras にフォールバック
- backend 不一致のAPI呼び出しは落とさず安全にダミー/HOLDを返す
- TensorFlow / SB3 は「必要になった時だけ」import（Gunicorn起動を軽量化）
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
from datetime import datetime, timedelta

# ===== Optional deps（遅延importのためダミーを用意） =====
tf = None          # type: ignore  # TensorFlow: 遅延import
PPO = None         # type: ignore  # SB3: 遅延import

# gymnasium は比較的軽量なのでそのまま（無ければ None）
try:
    import gymnasium as gym  # type: ignore
except Exception:
    gym = None  # type: ignore

from src.core.path_config import VERITAS_MODELS_DIR, ORACLE_FORECAST_JSON, DATA_DIR
from src.plan_data.standard_feature_schema import STANDARD_FEATURE_ORDER

log = logging.getLogger(__name__)
if not log.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")


def _import_from_module_class(spec: str):
    """'pkg.mod:ClassName' を import して Class を返す。"""
    if ":" not in spec:
        raise ValueError(f"Invalid module:Class spec: {spec}")
    mod, cls = spec.split(":", 1)
    m = import_module(mod)
    return getattr(m, cls)


# ===== SB3 既定パス解決（data/models/prometheus/PPO/obs8/latest/model.zip） =====
def _sb3_models_root() -> Path:
    return Path(DATA_DIR) / "models" / "prometheus" / "PPO" / "obs8"


def _resolve_latest_dir(base: Path) -> Optional[Path]:
    """latest シンボリックリンク → 実体。無ければ mtime 降順で最新を返す。"""
    if not base.exists():
        return None
    latest = base / "latest"
    if latest.exists():
        try:
            return latest.resolve()
        except Exception:
            pass
    cands = [p for p in base.iterdir() if p.is_dir() and p.name != "latest"]
    if not cands:
        return None
    return sorted(cands, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def _autodetect_default_model() -> Tuple[Optional[Path], Optional[str]]:
    """
    既定モデルの自動検出:
      1) SB3: data/models/prometheus/PPO/obs8/latest/model.zip
      2) Keras: VERITAS_MODELS_DIR/prometheus_oracle.keras
    戻り値: (path, backend) / (None, None)
    """
    # SB3
    sb3_root = _sb3_models_root()
    latest = _resolve_latest_dir(sb3_root)
    if latest:
        z = latest / "model.zip"
        if z.exists():
            return z, "sb3"
    # Keras fallback
    keras_path = Path(VERITAS_MODELS_DIR) / "prometheus_oracle.keras"
    if keras_path.exists():
        return keras_path, "keras"
    return None, None


def _safe_json(v: Path) -> Dict[str, Any]:
    try:
        if v.exists():
            return json.loads(v.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning("metadata.json 読み込み失敗: %s", e)
    return {}


def _ensure_tf():
    """TensorFlow を必要な時だけ import"""
    global tf
    if tf is None:
        os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")  # INFO抑制
        try:
            import tensorflow as _tf  # type: ignore
        except Exception as e:
            raise ImportError(f"TensorFlow の import に失敗: {e}")
        tf = _tf
    return tf


def _ensure_sb3():
    """stable-baselines3(PPO) を必要な時だけ import"""
    global PPO
    if PPO is None:
        try:
            from stable_baselines3 import PPO as _PPO  # type: ignore
        except Exception as e:
            raise ImportError(f"stable-baselines3 の import に失敗: {e}")
        PPO = _PPO
    return PPO


class PrometheusOracle:
    """
    - Keras: DataFrame → 連続値予測
    - SB3  : Env 1ステップ推論 → {BUY, SELL, HOLD}
    備考:
      * lazy=True なら初回利用時にロード
      * model_path に .zip を渡せば SB3、.keras/.h5/dir を渡せば Keras と判定
      * 未配置でもアプリを落とさない（API側で安全にハンドリング）
    """

    def __init__(
        self,
        model_path: Optional[Path | str] = None,
        feature_order: Optional[List[str]] = None,
        lazy: bool = True,
        deterministic: bool = True,
    ):
        self.feature_order = feature_order or STANDARD_FEATURE_ORDER
        self.lazy = bool(lazy)
        self.deterministic = bool(deterministic)

        # 既定は SB3 latest → 無ければ Keras（ロードはしない）
        if model_path:
            self.model_path = Path(model_path)
            self.backend = self._infer_backend(self.model_path)
        else:
            autod, be = _autodetect_default_model()
            self.model_path = autod
            self.backend = be or ""  # "", "sb3", "keras"

        self.model: Any = None  # 遅延ロード
        self._meta: Dict[str, Any] = {}
        self._loaded_path: Optional[Path] = None

        # 即ロードが必要ならここで
        if not self.lazy and self.model_path:
            self.load()

    # ---------- Backend 判定 ----------
    @staticmethod
    def _infer_backend(p: Path) -> str:
        s = p.suffix.lower()
        if s == ".zip":
            return "sb3"
        # ディレクトリ or keras/h5 は Keras 想定
        return "keras"

    # ---------- ロード ----------
    def load(self) -> "PrometheusOracle":
        if self.model_path is None:
            # 再度自動検出を試みる
            autod, be = _autodetect_default_model()
            self.model_path, self.backend = autod, (be or "")
            if self.model_path is None:
                raise FileNotFoundError("既定モデルが見つかりません（SB3 latest も Keras も不在）")

        p = self.model_path
        be = self._infer_backend(p)

        if be == "sb3":
            PPO_cls = _ensure_sb3()
            log.info("神託モデル読込(SB3): %s", p)
            self.model = PPO_cls.load(str(p), device="cpu")
            self.backend = "sb3"
        else:
            tf_mod = _ensure_tf()
            log.info("神託モデル読込(Keras): %s", p)
            self.model = tf_mod.keras.models.load_model(p)
            self.backend = "keras"

        # メタデータ（SB3のみ期待。Kerasは任意）
        if be == "sb3":
            meta_path = p.parent / "metadata.json"
        else:
            meta_path = p.parent / "metadata.json" if p.is_dir() else p.with_name("metadata.json")
        self._meta = _safe_json(meta_path)
        self._loaded_path = p
        return self

    def _ensure_loaded(self) -> bool:
        if self.model is not None:
            return True
        try:
            self.load()
            return True
        except Exception as e:
            log.warning("PrometheusOracle: モデルロードに失敗しました（遅延ロード）。理由: %s", e)
            return False

    # ---------- Keras 前処理 ----------
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
            # Keras じゃない時は落とさずダミー返却
            log.warning("predict_future は Keras 専用です（現在: %s）。ダミーを返します。", self.backend or "(none)")
            return pd.DataFrame({
                "date": [str(datetime.today())[:10]],
                "forecast": [np.nan],
                "lower": [np.nan],
                "upper": [np.nan],
                "decision_id": [decision_id],
                "caller": [caller],
                "reason": [f"backend={self.backend or 'none'} is not keras"],
            })

        if not self._ensure_loaded():
            return pd.DataFrame({
                "date": [str(datetime.today())[:10]],
                "forecast": [np.nan],
                "lower": [np.nan],
                "upper": [np.nan],
                "decision_id": [decision_id],
                "caller": [caller],
                "reason": ["keras model load failed"],
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
        y_pred = np.asarray(self.model.predict(df_input.values, verbose=0)).astype(np.float32).flatten()

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
        - backend=keras のときは安全に "HOLD"
        """
        if self.backend != "sb3":
            return "HOLD"
        if not self._ensure_loaded():
            return "HOLD"
        return self._decide_with_sb3()

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
            reset_out = env.reset(seed=42)
            if isinstance(reset_out, tuple) and len(reset_out) == 2:
                obs, _info = reset_out
            else:
                obs = reset_out
            action, _ = self.model.predict(obs, deterministic=self.deterministic)
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

    # ---------- 補助 ----------
    def status(self) -> Dict[str, Any]:
        """GUI/デバッグ用"""
        root = str(_sb3_models_root())
        latest_dir = None
        ld = _resolve_latest_dir(Path(root))
        if ld:
            latest_dir = str(ld)
        return {
            "backend": self.backend or "(none)",
            "ready": self.model is not None,
            "model_path": str(self._loaded_path or self.model_path) if (self._loaded_path or self.model_path) else None,
            "sb3_root": root,
            "latest_dir": latest_dir,
            "meta": self._meta,
        }

    def reload(self) -> "PrometheusOracle":
        """latest を再解決して再ロード（SB3ユーザ向け）"""
        self.model = None
        self._meta = {}
        self._loaded_path = None
        # 最新を取り直す
        autod, be = _autodetect_default_model()
        if autod:
            self.model_path = autod
            self.backend = be or self.backend
        return self.load()
