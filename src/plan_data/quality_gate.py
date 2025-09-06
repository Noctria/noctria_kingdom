# src/plan_data/quality_gate.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

from .contracts import FeatureBundle
from . import observability

Action = Literal["OK", "FLAT", "SCALE"]  # OK=通常 / FLAT=出力抑制 / SCALE=数量縮小

@dataclass
class QualityResult:
    ok: bool
    action: Action                 # "OK" | "FLAT" | "SCALE"
    qty_scale: float = 1.0
    reasons: List[str] = field(default_factory=list)
    # 監査・可観測性で使うための参照値（しきい値と実測値）
    max_lag_min: int = 0
    max_missing: float = 0.0
    data_lag_min: int = 0
    missing_ratio: float = 0.0

# 既定しきい値
DEFAULT_MAX_DATA_LAG_MIN = 30      # 30分遅延を超えたら抑制（FLAT）
DEFAULT_MAX_MISSING_RATIO = 0.05   # 5%超の欠損で縮小（SCALE）

def _clamp(v: float, lo: float, hi: float) -> float:
    return hi if v > hi else lo if v < lo else v

def _ctx_get(ctx: Any, key: str, default: Any = None) -> Any:
    """dict でもオブジェクトでも同じキーを安全に読む"""
    if ctx is None:
        return default
    if isinstance(ctx, dict):
        return ctx.get(key, default)
    return getattr(ctx, key, default)

def evaluate_quality(
    bundle: FeatureBundle,
    *,
    max_lag_min: int = DEFAULT_MAX_DATA_LAG_MIN,
    max_missing: float = DEFAULT_MAX_MISSING_RATIO,
    conn_str: Optional[str] = None,
) -> QualityResult:
    """
    データ品質ゲート（Plan層）:
      - data_lag_min（分）: 最新データの遅延（大きいほど悪い）
      - missing_ratio（0.0〜1.0）: 特徴量DFの欠損率（大きいほど悪い）

    判定ルール（簡易）:
      - data_lag_min > max_lag_min → action = "FLAT"（提案抑制）
      - missing_ratio > max_missing → action = "SCALE"（数量縮小; すでに FLAT なら FLAT を優先）
        * 縮小率は超過分に応じて線形に下げ、最小 0.3 にクランプ
    しきい値超過時は obs_alerts へも出力する。
    """
    ctx = getattr(bundle, "context", None)

    # 入力の妥当性（安全側）
    if max_lag_min < 0:
        max_lag_min = 0
    max_missing = _clamp(float(max_missing), 0.0, 1.0)

    # コンテキスト側の値も安全化（dict/obj 両対応）
    data_lag_min = _ctx_get(ctx, "data_lag_min", 0) or 0
    missing_ratio = _ctx_get(ctx, "missing_ratio", 0.0) or 0.0
    try:
        data_lag_min = int(data_lag_min)
    except Exception:
        data_lag_min = 0
    try:
        missing_ratio = float(missing_ratio)
    except Exception:
        missing_ratio = 0.0
    missing_ratio = _clamp(missing_ratio, 0.0, 1.0)

    reasons: List[str] = []
    action: Action = "OK"
    scale = 1.0
    trace_id = _ctx_get(ctx, "trace_id", None)
    symbol = _ctx_get(ctx, "symbol", "UNKNOWN")

    # 1) データ遅延チェック
    if data_lag_min > max_lag_min:
        reasons.append(f"data_lag_min={data_lag_min} > max_lag_min={max_lag_min}")
        action = "FLAT"  # 抑制（数量縮小より強い扱い）
        observability.emit_alert(
            kind="QUALITY.DATA_LAG",
            reason=f"data_lag_min {data_lag_min}min exceeds limit {max_lag_min}",
            severity="HIGH",
            trace_id=trace_id,
            details={"symbol": symbol, "data_lag_min": data_lag_min, "max_lag_min": max_lag_min},
            conn_str=conn_str,
        )

    # 2) 欠損率チェック
    if missing_ratio > max_missing:
        reasons.append(f"missing_ratio={missing_ratio:.3f} > max_missing={max_missing:.3f}")
        observability.emit_alert(
            kind="QUALITY.MISSING_RATIO",
            reason=f"missing_ratio {missing_ratio:.3f} exceeds limit {max_missing:.3f}",
            severity="MEDIUM",
            trace_id=trace_id,
            details={"symbol": symbol, "missing_ratio": missing_ratio, "max_missing": max_missing},
            conn_str=conn_str,
        )
        # 既に FLAT でなければ SCALE
        if action == "OK":
            action = "SCALE"
            over = missing_ratio - max_missing
            scale = _clamp(1.0 - over * 2.0, 0.3, 1.0)

    ok = (action == "OK")
    return QualityResult(
        ok=ok,
        action=action,
        qty_scale=scale,
        reasons=reasons,
        max_lag_min=max_lag_min,
        max_missing=max_missing,
        data_lag_min=int(data_lag_min),
        missing_ratio=float(missing_ratio),
    )
