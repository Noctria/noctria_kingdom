from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import uuid4

from decision.decision_engine import DecisionEngine
from plan_data.inventor import generate_proposals  # 候補生成（純粋関数）
from plan_data.noctus_gate import (
    FeatureBundle,          # Pydantic BaseModel (V1/V2)
    StrategyProposal,       # Pydantic BaseModel
)

# Harmonia: リランク（存在すれば使う）
try:
    from codex.agents.harmonia import rerank_candidates as _harmonia_rerank
except Exception:  # noqa: BLE001
    _harmonia_rerank = None


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """attr / dict 両対応の安全取得"""
    if hasattr(obj, key):
        try:
            return getattr(obj, key)
        except Exception:  # noqa: BLE001
            pass
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


def _summarize_proposals(proposals: List[StrategyProposal], k: int = 10) -> List[Dict[str, Any]]:
    """StrategyProposal（Pydantic）を要約（属性アクセスで安全に）"""
    out: List[Dict[str, Any]] = []
    for p in proposals[:k]:
        out.append(
            {
                "strategy": _get(p, "strategy"),
                "intent": _get(p, "intent"),
                "qty": _get(p, "qty_raw"),
                "score": _get(p, "risk_adjusted", _get(p, "risk_score")),
                "id": _get(p, "id"),
            }
        )
    return out


def _fallback_size(decision: Dict[str, Any], proposals: List[StrategyProposal]) -> bool:
    """
    DecisionEngine の size が 0.0 の場合の保険。
    最上位候補の qty_raw * min(1.0, risk_adjusted or risk_score) を採用。
    """
    try:
        size = float(decision.get("size", 0.0) or 0.0)
    except Exception:  # noqa: BLE001
        size = 0.0

    if size > 0:
        return False

    if not proposals:
        return False

    top = proposals[0]
    qty = _get(top, "qty_raw", 0.0) or 0.0
    score = _get(top, "risk_adjusted", _get(top, "risk_score", 0.5)) or 0.5
    try:
        qty = float(qty)
    except Exception:  # noqa: BLE001
        qty = 0.0
    try:
        score = float(score)
    except Exception:  # noqa: BLE001
        score = 0.5

    size_new = max(0.0, qty * min(1.0, score))
    if size_new <= 0:
        return False

    reason = (decision.get("reason") or "") + " | fallback_size_applied"
    decision.update({"size": size_new, "reason": reason})
    return True


def _ensure_bundle(fb: Optional[Any]) -> FeatureBundle:
    """
    入力 fb（dict or FeatureBundle or None）を **確実に FeatureBundle** に整える。
    - FeatureContext を *直接 new しない*（← Any の可能性があるため）
    - context は辞書で組み立て、FeatureBundle に渡して Pydantic に解釈させる
    """
    if isinstance(fb, FeatureBundle):
        return fb

    data: Dict[str, Any] = fb or {}
    features = data.get("features") or {}
    trace_id = data.get("trace_id") or str(uuid4())
    context_in = data.get("context") or {}

    symbol = _get(context_in, "symbol", "USDJPY")
    timeframe = _get(context_in, "timeframe", "M15")

    ctx_dict: Dict[str, Any] = {"symbol": symbol, "timeframe": timeframe}
    if "missing_ratio" in context_in:
        ctx_dict["missing_ratio"] = _get(context_in, "missing_ratio", 0.0)
    if "data_lag_min" in context_in:
        ctx_dict["data_lag_min"] = _get(context_in, "data_lag_min", 0)

    try:
        return FeatureBundle(features=features, trace_id=trace_id, context=ctx_dict)
    except Exception:
        return FeatureBundle(features={}, trace_id=trace_id, context=ctx_dict)


def run_inventor_and_decide(
    fb: Optional[Any] = None,
    conn_str: Optional[str] = None,
    use_harmonia: bool = True,
) -> Dict[str, Any]:
    """
    Airflow から呼ぶブリッジ:
      1) FeatureBundle を確実化
      2) Inventor で候補生成
      3) Harmonia で（あれば）リランク
      4) DecisionEngine で決定
      5) size==0 の場合にフォールバック適用
    """
    bundle: FeatureBundle = _ensure_bundle(fb)

    proposals: List[StrategyProposal] = generate_proposals(bundle)

    if use_harmonia and _harmonia_rerank:
        try:
            quality = {}
            ctx = _get(bundle, "context", {}) or {}
            mr = _get(ctx, "missing_ratio", None)
            if mr is not None:
                quality["missing_ratio"] = mr
            dl = _get(ctx, "data_lag_min", None)
            if dl is not None:
                quality["data_lag_min"] = dl

            proposals = list(_harmonia_rerank(proposals, context=ctx, quality=quality))
        except Exception as e:  # noqa: BLE001
            from airflow.utils.log.logging_mixin import LoggingMixin
            LoggingMixin().log.info("[Harmonia] Rerank skipped or failed: %r", e)

    eng = DecisionEngine()
    record, decision = eng.decide(bundle, proposals=proposals, conn_str=conn_str)

    _fallback_size(decision, proposals)

    return {
        "trace_id": _get(bundle, "trace_id"),
        "proposal_summary": _summarize_proposals(proposals, k=10),
        "decision": decision,
    }
