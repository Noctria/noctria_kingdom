from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional
import json as _json
import sys as _sys

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


def _emit_alert(kind: str, message: str = "", **fields) -> None:
    """
    安全アラート送出:
      1) observability.emit_alert を試みる（未知kwargsも透過）
      2) 常に stdout に 1行JSON を出力（テストが確実に拾える）
      例外は握りつぶし、呼び出し元を落とさない
    """
    try:
        if hasattr(observability, "emit_alert"):
            observability.emit_alert(kind=kind, message=message, **fields)  # type: ignore
    except Exception:
        pass  # stdout フォールバックへ

    try:
        payload = {"kind": kind, "message": message}
        payload.update(fields)
        print(_json.dumps(payload, ensure_ascii=False))
        _sys.stdout.flush()
    except Exception:
        pass


def evaluate_quality(
    bundle: FeatureBundle,
    *,
    max_lag_min: int = DEFAULT_MAX_DATA_LAG_MIN,
    max_missing: float = DEFAULT_MAX_MISSING_RATIO,
    conn_str: Optional[str] = None,
) -> QualityResult:
    """
    データ品質ゲート（Plan層）
      - data_lag_min（分）: 最新データの遅延（大きいほど悪い）
      - missing_ratio（0.0〜1.0）: 特徴量DFの欠損率（大きいほど悪い）

    判定（簡易）:
      - data_lag_min > max_lag_min → action = "FLAT"（提案抑制）
      - missing_ratio > max_missing → action = "SCALE"（数量縮小; すでに FLAT なら FLAT 優先）
        * 縮小率は超過分に応じて線形に下げ、最小 0.3 にクランプ
    しきい値超過時は obs_alerts へも出力。
    """
    ctx = getattr(bundle, "context", None)

    # 入力の妥当性（安全側）
    if max_lag_min < 0:
        max_lag_min = 0
    max_missing = _clamp(float(max_missing), 0.0, 1.0)

    # コンテキスト値の安全化（dict/obj 両対応）
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

    # テスト互換の trace キー（trace優先、無ければ trace_id）
    trace = _ctx_get(ctx, "trace", _ctx_get(ctx, "trace_id", None))
    symbol = _ctx_get(ctx, "symbol", "UNKNOWN")
    timeframe = _ctx_get(ctx, "timeframe", "UNKNOWN")

    # 1) データ遅延チェック
    if data_lag_min > max_lag_min:
        reasons.append(f"data_lag_min={data_lag_min} > max_lag_min={max_lag_min}")
        action = "FLAT"  # 抑制（数量縮小より強い）
        _emit_alert(
            "QUALITY.DATA_LAG",
            message=f"data_lag_min={data_lag_min}",
            # テストが参照する 'reason'
            reason=f"data_lag_min {data_lag_min}min exceeds limit {max_lag_min}",
            severity="HIGH",
            trace=trace,
            symbol=symbol,
            timeframe=timeframe,
            # テストが参照する 'details' ネスト
            details={
                "data_lag_min": data_lag_min,
                "max_lag_min": max_lag_min,
            },
            # 互換のため上位にも（あっても害はない）
            data_lag_min=data_lag_min,
            max_lag_min=max_lag_min,
            conn_str=conn_str,
        )

    # 2) 欠損率チェック
    if missing_ratio > max_missing:
        reasons.append(f"missing_ratio={missing_ratio:.3f} > max_missing={max_missing:.3f}")
        _emit_alert(
            "QUALITY.MISSING_RATIO",
            message=f"missing_ratio={missing_ratio:.3f}",
            # テストが参照する 'reason'
            reason=f"missing_ratio {missing_ratio:.3f} exceeds limit {max_missing:.3f}",
            severity="MEDIUM",
            trace=trace,
            symbol=symbol,
            timeframe=timeframe,
            # テストが参照する 'details' ネスト
            details={
                "missing_ratio": missing_ratio,
                "max_missing": max_missing,
            },
            # 互換のため上位にも
            missing_ratio=missing_ratio,
            max_missing=max_missing,
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
