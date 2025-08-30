# src/plan_data/strategy_adapter.py
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, runtime_checkable, Iterable, Tuple

import pandas as pd

# 観測は失敗しても握りつぶす方針（オフラインでも動く）
try:
    from plan_data.observability import log_infer_call  # type: ignore
except Exception:
    from src.plan_data.observability import log_infer_call  # type: ignore

try:
    from plan_data.trace import get_trace_id, new_trace_id  # type: ignore
except Exception:
    from src.plan_data.trace import get_trace_id, new_trace_id  # type: ignore


# --- Contracts (超軽量版) ---

@dataclass
class FeatureBundle:
    df: pd.DataFrame
    context: Any
    feature_order: Optional[list[str]] = None
    version: str = "1.0.0"

    def tail_row(self) -> pd.Series:
        return self.df.iloc[-1] if len(self.df) else pd.Series(dtype="float64")


@dataclass
class StrategyProposal:
    symbol: str
    direction: str        # "LONG" / "SHORT" / "FLAT"
    qty: float
    confidence: float     # 0.0 ~ 1.0
    reasons: list[str]
    meta: Dict[str, Any]
    schema_version: str = "1.0.0"


# --- Protocols ---
@runtime_checkable
class _ProposeLike(Protocol):
    def propose(self, features: Any, **kwargs) -> StrategyProposal: ...


@runtime_checkable
class _PredictLike(Protocol):
    def predict_future(self, features: Any, **kwargs) -> StrategyProposal: ...


# --- Utils ---
_VALID_DIRECTIONS = {"LONG", "SHORT", "FLAT"}


def _to_list_str(x: Any) -> list[str]:
    if x is None:
        return []
    if isinstance(x, str):
        return [x]
    if isinstance(x, Iterable):
        return [str(v) for v in x]
    return [str(x)]


def _normalize_proposal(p: StrategyProposal) -> StrategyProposal:
    direction = (p.direction or "FLAT").upper()
    if direction not in _VALID_DIRECTIONS:
        direction = "FLAT"

    try:
        qty = float(p.qty)
    except Exception:
        qty = 0.0
    try:
        conf = float(p.confidence)
    except Exception:
        conf = 0.0
    conf = max(0.0, min(1.0, conf))

    reasons = _to_list_str(p.reasons)

    return StrategyProposal(
        symbol=str(p.symbol or p.meta.get("symbol") or "UNKNOWN"),
        direction=direction,
        qty=qty,
        confidence=conf,
        reasons=reasons,
        meta=dict(p.meta or {}),
        schema_version=str(p.schema_version or "1.0.0"),
    )


def _coerce_to_proposal(obj: Any, default_symbol: str) -> StrategyProposal:
    if isinstance(obj, StrategyProposal):
        return _normalize_proposal(obj)

    if isinstance(obj, dict):
        cand = StrategyProposal(
            symbol=str(obj.get("symbol") or default_symbol or "UNKNOWN"),
            direction=str(obj.get("direction") or "FLAT"),
            qty=float(obj.get("qty") or 0.0),
            confidence=float(obj.get("confidence") or 0.0),
            reasons=_to_list_str(obj.get("reasons")),
            meta=dict(obj.get("meta") or {}),
            schema_version=str(obj.get("schema_version") or "1.0.0"),
        )
        return _normalize_proposal(cand)

    try:
        cand = StrategyProposal(
            symbol=str(getattr(obj, "symbol", default_symbol) or default_symbol or "UNKNOWN"),
            direction=str(getattr(obj, "direction", "FLAT")),
            qty=float(getattr(obj, "qty", 0.0)),
            confidence=float(getattr(obj, "confidence", 0.0)),
            reasons=_to_list_str(getattr(obj, "reasons", [])),
            meta=dict(getattr(obj, "meta", {}) or {}),
            schema_version=str(getattr(obj, "schema_version", "1.0.0")),
        )
        return _normalize_proposal(cand)
    except Exception:
        return StrategyProposal(
            symbol=str(default_symbol or "UNKNOWN"),
            direction="FLAT",
            qty=0.0,
            confidence=0.0,
            reasons=["invalid proposal object"],
            meta={"raw": repr(obj)},
            schema_version="1.0.0",
        )


def _bundle_to_dict_and_order(features: FeatureBundle) -> Tuple[Dict[str, Any], Optional[list[str]]]:
    base: Dict[str, Any] = {}
    try:
        tail = features.tail_row()
        if isinstance(tail, pd.Series):
            base.update({str(k): tail[k] for k in tail.index})
    except Exception:
        pass

    ctx = getattr(features, "context", None)
    if ctx:
        ctx_dict = ctx.dict() if hasattr(ctx, "dict") else dict(ctx)
        for k, v in ctx_dict.items():
            key = f"ctx_{k}" if k not in base else k
            if key not in base:
                base[key] = v

    return base, (features.feature_order or None)


def _call_strategy_with_auto_compat(strategy: Any, call_name: str, features: FeatureBundle, **kwargs) -> Any:
    fn = getattr(strategy, call_name)

    feat_dict, order = _bundle_to_dict_and_order(features)
    try_kwargs = dict(kwargs)
    if order is not None and "feature_order" not in try_kwargs:
        try_kwargs["feature_order"] = order
    try:
        return fn(feat_dict, **try_kwargs)
    except Exception:
        return fn(features, **kwargs)


# --- Main wrapper ---
def propose_with_logging(
    strategy: Any,
    features: FeatureBundle,
    *,
    model_name: Optional[str] = None,
    model_version: Optional[str] = None,
    timeout_sec: Optional[float] = None,
    trace_id: Optional[str] = None,
    conn_str: Optional[str] = None,
    **kwargs,
) -> StrategyProposal:
    model = model_name or getattr(getattr(strategy, "__class__", None), "__name__", str(type(strategy).__name__))
    ver = model_version or getattr(strategy, "VERSION", "dev")

    # --- 修正: context は dict ではなく PydanticModel の可能性あり ---
    ctx = getattr(features, "context", None)
    trace_id = (
        trace_id
        or getattr(ctx, "trace_id", None)
        or get_trace_id()
        or new_trace_id(
            symbol=str(getattr(ctx, "symbol", "MULTI")),
            timeframe=str(getattr(ctx, "timeframe", "1d")),
        )
    )

    t0 = time.time()
    success = False
    proposal: Optional[StrategyProposal] = None

    try:
        if isinstance(strategy, _ProposeLike) or hasattr(strategy, "propose"):
            raw = _call_strategy_with_auto_compat(strategy, "propose", features, **kwargs)
        elif isinstance(strategy, _PredictLike) or hasattr(strategy, "predict_future"):
            raw = _call_strategy_with_auto_compat(strategy, "predict_future", features, **kwargs)
        else:
            raise AttributeError(f"{model} has neither propose() nor predict_future().")

        proposal = _coerce_to_proposal(raw, default_symbol=str(getattr(ctx, "symbol", "MULTI")))
        success = True
        return proposal
    finally:
        dur_ms = int((time.time() - t0) * 1000)
        if timeout_sec is not None and (dur_ms / 1000.0) > timeout_sec:
            success = False
        try:
            log_infer_call(
                conn_str or None,
                model=model,
                ver=str(ver),
                dur_ms=dur_ms,
                success=bool(success),
                feature_staleness_min=int(getattr(ctx, "data_lag_min", 0) or 0),
                trace_id=trace_id,
            )
        except Exception:
            pass
