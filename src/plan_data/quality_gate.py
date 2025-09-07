# src/plan_data/quality_gate.py
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

# Airflow 環境で Variables を使えない場合に備え、環境変数フォールバックも用意
def _get_var(name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Airflow Variables -> 環境変数(FALLBACK) の順で取得。
    - GUI: Admin > Variables で設定した値を最優先。
    - 非Airflow/ローカル: os.environ から拾う。
    """
    try:
        # Airflow があれば Variable.get を使う
        from airflow.models import Variable  # type: ignore
        val = Variable.get(name)  # may raise KeyError
        if isinstance(val, str):
            return val
    except Exception:
        pass

    # Fallback to env
    import os
    return os.environ.get(name, default)


def _to_float(s: Optional[str], default: float) -> float:
    try:
        if s is None:
            return default
        return float(s)
    except Exception:
        return default


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class QualityResultLite:
    """
    DAG が期待する最小スキーマ（pydantic の有無に左右されない）
    """
    passed: bool
    reason: str
    details: Dict[str, Any]


# ------------------------------------------------------------
# しきい値（Airflow Variables / 環境変数）
# ------------------------------------------------------------
def _load_thresholds() -> Tuple[float, float]:
    """
    Returns:
        (missing_max, lag_max_min)
    """
    missing_max = _to_float(_get_var("NOCTRIA_QG_MISSING_MAX"), 0.20)
    lag_max_min = _to_float(_get_var("NOCTRIA_QG_LAG_MAX_MIN"), 10.0)
    return missing_max, lag_max_min


# ------------------------------------------------------------
# 実測推定: missing_ratio / data_lag_min
# ------------------------------------------------------------
_NUMERIC_TYPES = (int, float)


def _is_nan(x: Any) -> bool:
    return isinstance(x, float) and math.isnan(x)


def _estimate_missing_ratio(features: Dict[str, Any]) -> float:
    """
    features から欠損率を推定。
    - 明示的に features["missing_ratio"] が与えられていればそれを優先
    - 無ければ、features の key/value を走査して None/NaN を欠損として比率化
      * ネストは深追いしない（軽量・高速優先）
    """
    try:
        v = features.get("missing_ratio")
        if isinstance(v, _NUMERIC_TYPES) and not _is_nan(v):
            return max(0.0, min(float(v), 1.0))
    except Exception:
        pass

    # 簡易推定: 直接の key/value のみ対象
    total = 0
    miss = 0
    for k, v in (features or {}).items():
        total += 1
        if v is None:
            miss += 1
        elif isinstance(v, float) and math.isnan(v):
            miss += 1
    if total == 0:
        return 0.0
    return max(0.0, min(miss / total, 1.0))


def _estimate_data_lag_min(context: Dict[str, Any]) -> float:
    """
    context からデータ遅延(分)を推定。
    - 明示的に context["data_lag_min"] があれば優先
    - 無ければ context["last_price_ts"]（UTC ISO文字列 or epoch秒）から算出
    - いずれも無い場合は 0.0 を返す（安全側運用。必要に応じてデフォルトを上げてよい）
    """
    # 優先: 直接指定
    try:
        v = context.get("data_lag_min")
        if isinstance(v, _NUMERIC_TYPES) and not _is_nan(v):
            return max(0.0, float(v))
    except Exception:
        pass

    # last_price_ts (ISO8601 or epoch) → 現在との差分
    last_ts = context.get("last_price_ts")
    if last_ts is not None:
        try:
            if isinstance(last_ts, str):
                # ISO8601 (例: "2025-09-07T08:46:11.215941+00:00")
                ts = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
            elif isinstance(last_ts, (int, float)):
                ts = datetime.fromtimestamp(float(last_ts), tz=timezone.utc)
            else:
                ts = None
            if ts is not None:
                delta = _utcnow() - ts
                return max(0.0, delta.total_seconds() / 60.0)
        except Exception:
            pass

    # 推定不能なら 0.0
    return 0.0


# ------------------------------------------------------------
# Public API
# ------------------------------------------------------------
def evaluate_quality(bundle: Any) -> Any:
    """
    FeatureBundle (pydantic v1/v2 / dict) を受けて、品質を判定。
    返却は「pydanticがあればそれ」「無ければ dataclass」「最悪 dict」いずれでも運用可能。

    Input 例 (dict の場合):
        {
          "features": {...},
          "trace_id": "...",
          "context": {"symbol":"USDJPY","timeframe":"M15", "last_price_ts": "..."}  # 任意
        }
    """
    # -------- FeatureBundle 抽出（pydantic v1/v2 or dict or 任意）--------
    def _get_attr(o: Any, name: str, default: Any = None) -> Any:
        if o is None:
            return default
        if isinstance(o, dict):
            return o.get(name, default)
        try:
            return getattr(o, name)
        except Exception:
            return default

    features: Dict[str, Any] = _get_attr(bundle, "features", {}) or {}
    context: Dict[str, Any] = _get_attr(bundle, "context", {}) or {}
    trace_id: str = _get_attr(bundle, "trace_id", "") or ""

    # -------- 実測/推定値の計算 --------
    missing_ratio = _estimate_missing_ratio(features)
    data_lag_min = _estimate_data_lag_min(context)

    missing_max, lag_max_min = _load_thresholds()

    passed = (missing_ratio <= missing_max) and (data_lag_min <= lag_max_min)

    if passed:
        reason = "quality_ok"
    else:
        # 詳細理由を整形
        parts = []
        if missing_ratio > missing_max:
            parts.append(f"missing_ratio {missing_ratio:.3f}>{missing_max:.3f}")
        if data_lag_min > lag_max_min:
            parts.append(f"data_lag_min {data_lag_min:.1f}>{lag_max_min:.1f}")
        reason = "quality_threshold_not_met: " + ", ".join(parts)

    details = {
        "missing_ratio": float(missing_ratio),
        "data_lag_min": float(data_lag_min),
        "thresholds": {
            "missing_max": float(missing_max),
            "lag_max_min": float(lag_max_min),
        },
    }

    # -------- 返却（pydantic があればそれを優先）--------
    # v2: BaseModel.model_construct
    try:
        from pydantic import BaseModel  # type: ignore

        class _QR(BaseModel):
            passed: bool
            reason: str
            details: Dict[str, Any]

        return _QR(passed=passed, reason=reason, details=details)
    except Exception:
        pass

    # dataclass 返却（DAG側の _qres_to_dict が各種形式を安全に吸収）
    return QualityResultLite(passed=passed, reason=reason, details=details)
