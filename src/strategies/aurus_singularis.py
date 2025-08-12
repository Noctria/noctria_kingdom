#!/usr/bin/env python3
# coding: utf-8
"""
🎯 Aurus Singularis
- 標準 feature_order に従って入力を受け取り、売買提案を返す Strategy
- TensorFlow は任意依存：存在すれば学習済みモデル or 簡易モデルで推論、無ければ軽量ヒューリスティックにフォールバック
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

import numpy as np

# ---- logger ----
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

# ---- optional deps / paths ----
try:
    import tensorflow as tf  # type: ignore
    TF_AVAILABLE = True
except Exception:
    tf = None  # type: ignore
    TF_AVAILABLE = False
    logger.warning("TensorFlow is not installed; Aurus will use a lightweight heuristic fallback.")

try:
    # 既存パス定義（存在しない環境でも落とさない）
    from src.core.path_config import VERITAS_MODELS_DIR  # type: ignore
except Exception:
    VERITAS_MODELS_DIR = Path("models/registry")  # safe fallback

try:
    from src.plan_data.standard_feature_schema import STANDARD_FEATURE_ORDER  # type: ignore
except Exception:
    STANDARD_FEATURE_ORDER: List[str] = []  # 与えられなければ propose 入力のキー順を使う


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        v = float(x)
        if np.isnan(v):
            return float(default)
        return v
    except Exception:
        return float(default)


class AurusSingularis:
    """
    - feature_order: List[str] 入力 dict をこの順にベクトル化（欠損は 0.0）
    - model_path   : 任意。指定 or 既定パスが存在し、TensorFlow 利用可能ならロードを試みる
    """
    def __init__(
        self,
        model_path: Optional[Path] = None,
        feature_order: Optional[List[str]] = None,
    ):
        self.feature_order: List[str] = feature_order or list(STANDARD_FEATURE_ORDER)
        # 既定の保存先（存在しなくてもOK、ロード時のみ参照）
        self.model_path: Path = model_path or (Path(VERITAS_MODELS_DIR) / "aurus_singularis_v3.keras")
        self.model = self._maybe_load_or_build_model(input_dim=len(self.feature_order))

    # ------------------------------
    # Model load/build （TFがある時だけ）
    # ------------------------------
    def _maybe_load_or_build_model(self, input_dim: int):
        if not TF_AVAILABLE:
            return None

        # 既存モデルがあればロード
        try:
            if self.model_path.exists():
                logger.info("📦 モデル読込: %s", self.model_path)
                return tf.keras.models.load_model(self.model_path)  # type: ignore
        except Exception as e:
            logger.warning("モデル読込失敗（ヒューリスティックへフォールバック）: %s", e)

        # ざっくりした小型モデル（学習前提／デモ用）
        logger.info("🧪 新規モデル構築 (input_dim=%d)", input_dim)
        try:
            model = tf.keras.Sequential([
                tf.keras.layers.Input(shape=(input_dim,)),
                tf.keras.layers.Dense(64, activation="relu"),
                tf.keras.layers.Dropout(0.1),
                tf.keras.layers.Dense(32, activation="relu"),
                tf.keras.layers.Dense(3, activation="softmax"),  # 0=SELL, 1=HOLD, 2=BUY
            ])
            model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
            return model
        except Exception as e:
            logger.warning("モデル構築失敗（ヒューリスティックへフォールバック）: %s", e)
            return None

    def save_model(self) -> None:
        if not TF_AVAILABLE or self.model is None:
            logger.info("TensorFlow モデルが無いため save はスキップ")
            return
        try:
            self.model_path.parent.mkdir(parents=True, exist_ok=True)
            self.model.save(self.model_path)
            logger.info("💾 モデル保存: %s", self.model_path)
        except Exception as e:
            logger.warning("モデル保存失敗: %s", e)

    # ------------------------------
    # Preprocess
    # ------------------------------
    def _preprocess(self, feature_dict: Dict[str, Any]) -> np.ndarray:
        # feature_order 未設定なら、入力のキー順（安定させたい場合は外部で固定順を渡す）
        order = self.feature_order or list(feature_dict.keys())
        vec = np.array([_safe_float(feature_dict.get(k, 0.0)) for k in order], dtype=np.float32)
        return vec.reshape(1, -1)

    # ------------------------------
    # Heuristic fallback (no TF)
    # ------------------------------
    def _heuristic_propose(self, feat: Dict[str, Any]) -> Dict[str, Any]:
        """
        シンプルなルール:
          - usdjpy_rsi_14d < 35 → BUY
          - usdjpy_rsi_14d > 65 → SELL
          - それ以外 → HOLD
        ニューススパイクなど軽いシグナルも参照して confidence を微調整。
        """
        rsi = _safe_float(feat.get("usdjpy_rsi_14d"), np.nan)
        news_spike = int(_safe_float(feat.get("news_spike_flag"), 0.0) > 0.5)
        gc_flag = int(_safe_float(feat.get("usdjpy_gc_flag"), 0.0) > 0.5)

        signal = "HOLD"
        base_conf = 0.5

        if not np.isnan(rsi):
            if rsi < 35:
                signal = "BUY"
                base_conf = 0.58
            elif rsi > 65:
                signal = "SELL"
                base_conf = 0.58

        # 補助特徴で confidence を微修正
        base_conf += 0.05 * (gc_flag if signal == "BUY" else 0)
        base_conf += 0.03 * (news_spike if signal != "HOLD" else 0)
        base_conf = float(max(0.5, min(0.85, base_conf)))

        return {
            "name": "AurusSingularis",
            "type": "comprehensive_analysis_report",
            "signal": signal,                  # "BUY" | "SELL" | "HOLD"
            "confidence": round(base_conf, 4), # 0.5〜0.85
            "priority": "high" if base_conf >= 0.7 else "medium",
            "reason": "heuristic_rsi_rule",
        }

    # ------------------------------
    # Public API
    # ------------------------------
    def train(
        self,
        feat_df: "np.ndarray | Any",  # pandas.DataFrame 互換もOK
        label_col: str = "label",
        epochs: int = 10,
        batch_size: int = 32,
    ) -> None:
        if not TF_AVAILABLE:
            logger.info("TensorFlow が無いため train はスキップ（ヒューリスティック運用）")
            return

        try:
            import pandas as pd  # optional; 与えられた型に応じて抽出
            if isinstance(feat_df, pd.DataFrame):
                feature_order = [c for c in feat_df.columns if c != label_col]
                X = feat_df[feature_order].to_numpy(dtype=np.float32)
                y = feat_df[label_col].to_numpy()
                self.feature_order = feature_order
            else:
                # (X, y) タプルを想定
                X, y = feat_df
                X = np.asarray(X, dtype=np.float32)
        except Exception:
            # 最後の砦： (X, y) タプルを想定
            X, y = feat_df
            X = np.asarray(X, dtype=np.float32)

        self.model = self._maybe_load_or_build_model(input_dim=X.shape[1])
        if self.model is None:
            logger.info("TensorFlow モデル構築不可のため train はスキップ")
            return

        self.model.fit(X, y, epochs=epochs, batch_size=batch_size, verbose=0)
        self.save_model()

    def propose(
        self,
        feature_dict: Dict[str, Any],
        decision_id: Optional[str] = None,
        caller: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        # TF モデルでの推論を試み、無ければヒューリスティック
        if TF_AVAILABLE and self.model is not None:
            try:
                x = self._preprocess(feature_dict)
                probs = self.model.predict(x, verbose=0)[0]
                cls = int(np.argmax(probs))  # 0=SELL,1=HOLD,2=BUY
                signal = {0: "SELL", 1: "HOLD", 2: "BUY"}.get(cls, "HOLD")
                conf = float(np.max(probs))
                out = {
                    "name": "AurusSingularis",
                    "type": "comprehensive_analysis_report",
                    "signal": signal,
                    "confidence": round(conf, 4),
                    "priority": "high" if conf > 0.7 else "medium",
                    "reason": "tf_model",
                }
            except Exception as e:
                logger.warning("TF 推論失敗（フォールバック適用）: %s", e)
                out = self._heuristic_propose(feature_dict)
        else:
            out = self._heuristic_propose(feature_dict)

        # メタ付与（上流で使いやすいように）
        out.update({
            "decision_id": decision_id,
            "caller": caller,
        })
        if reason:
            out["reason"] = f"{out.get('reason','')}; {reason}".strip("; ")
        return out


__all__ = ["AurusSingularis"]
