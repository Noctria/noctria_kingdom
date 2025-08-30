# src/plan_data/strategy_adapter.py
from __future__ import annotations

import time
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

# 正典の contracts へ統一
try:
    from plan_data.contracts import FeatureBundle, StrategyProposal, adapt_proposal_dict_v1  # type: ignore
except Exception:
    from src.plan_data.contracts import FeatureBundle, StrategyProposal, adapt_proposal_dict_v1  # type: ignore


# --- Strategy 呼出契約（プロトコル） ---
@runtime_checkable
class _ProposeLike(Protocol):
    def propose(self, features: Any, **kwargs) -> StrategyProposal: ...


@runtime_checkable
class _PredictLike(Protocol):
    def predict_future(self, features: Any, **kwargs) -> StrategyProposal: ...


# --- 内部ユーティリティ ---

_VALID_DIRECTIONS = {"LONG", "SHORT", "FLAT"}


def _to_list_str(x: Any) -> list[str]:
    if x is None:
        return []
    if isinstance(x, str):
        return [x]
    if isinstance(x, Iterable):
        return [str(v) for v in x]
    return [str(x)]


def _normalize_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """方向・qty・confidence を軽く正規化して StrategyProposal に渡せる dict にする"""
    d = dict(d)
    # direction 正規化
    direction = str(d.get("direction") or d.get("intent") or "FLAT").upper()
    if direction not in _VALID_DIRECTIONS:
        direction = "FLAT"
    d["intent"] = direction if direction in ("LONG", "SHORT") else "FLAT"

    # qty/confidence 正規化
    try:
        d["qty_raw"] = float(d.get("qty_raw", d.get("qty", 0.0)))
    except Exception:
        d["qty_raw"] = 0.0
    try:
        conf = float(d.get("confidence", 0.0))
    except Exception:
        conf = 0.0
    d["confidence"] = max(0.0, min(1.0, conf))

    # reasons
    d["reasons"] = _to_list_str(d.get("reasons", []))
    return d


def _coerce_to_proposal(obj: Any, default_symbol: str) -> StrategyProposal:
    """dict/NamedTuple/他クラスから StrategyProposal へ極力寄せる"""
    if isinstance(obj, StrategyProposal):
        return obj

    if isinstance(obj, dict):
        base = adapt_proposal_dict_v1(obj)
        base.setdefault("symbol", default_symbol or "UNKNOWN")
        return StrategyProposal(**_normalize_dict(base))

    # NamedTuple や属性持ちオブジェクト
    try:
        base = {
            "symbol": getattr(obj, "symbol", default_symbol or "UNKNOWN"),
            "intent": getattr(obj, "intent", getattr(obj, "direction", "FLAT")),
            "qty_raw": getattr(obj, "qty_raw", getattr(obj, "qty", 0.0)),
            "confidence": getattr(obj, "confidence", 0.0),
            "reasons": getattr(obj, "reasons", []),
            "risk_score": getattr(obj, "risk_score", 0.5),
            "strategy": getattr(obj, "strategy", type(obj).__name__),
            "trace_id": getattr(obj, "trace_id", "N/A"),
        }
        return StrategyProposal(**_normalize_dict(base))
    except Exception:
        return StrategyProposal(
            strategy="invalid",
            intent="FLAT",
            qty_raw=0.0,
            confidence=0.0,
            reasons=["invalid proposal object"],
            trace_id="N/A",
        )


def _bundle_to_dict_and_order(features: FeatureBundle) -> Tuple[Dict[str, Any], Optional[list[str]]]:
    """
    Aurus など「dict で .get する」戦略向けに FeatureBundle を辞書へ変換。
    - ベース: 最新行（tail）を dict 化
    - 併せて context も 'ctx_*' で補助的に混ぜる（キー衝突は tail が優先）
    - feature_order はそのまま返す（必要なら戦略へ渡す）
    """
    base: Dict[str, Any] = {}
    try:
        tail = features.df.iloc[-1] if len(features.df) else None
        if tail is not None and isinstance(tail, pd.Series):
            base.update({str(k): tail[k] for k in tail.index})
    except Exception:
        pass

    ctx = dict(features.context or {})
    for k, v in ctx.items():
        key = f"ctx_{k}" if k not in base else k
        if key not in base:
            base[key] = v

    return base, (features.feature_order or None)


def _call_strategy_with_auto_compat(strategy: Any, call_name: str, features: FeatureBundle, **kwargs) -> Any:
    """
    互換レイヤ：
      1) dict で呼ぶ（旧API互換）
      2) ダメなら FeatureBundle をそのまま渡す（新API対応）
    """
    fn = getattr(strategy, call_name)

    # 1st: dict でトライ
    feat_dict, order = _bundle_to_dict_and_order(features)
    try_kwargs = dict(kwargs)
    if order is not None and "feature_order" not in try_kwargs:
        try_kwargs["feature_order"] = order
    try:
        return fn(feat_dict, **try_kwargs)
    except Exception:
        return fn(features, **kwargs)


# --- Adapter ---

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
    """
    共通呼び出しラッパ
    """
    model = model_name or getattr(getattr(strategy, "__class__", None), "__name__", str(type(strategy).__name__))
    ver = model_version or getattr(strategy, "VERSION", "dev")

    trace_id = trace_id or get_trace_id() or new_trace_id(
        symbol=str(features.context.get("symbol", "MULTI")),
        timeframe=str(features.context.get("timeframe", "1d")),
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

        proposal = _coerce_to_proposal(raw, default_symbol=str(features.context.get("symbol", "MULTI")))
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
                feature_staleness_min=int(features.context.get("feature_staleness_min", 0) or 0),
                trace_id=trace_id,
            )
        except Exception:
            pass
