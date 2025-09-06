from __future__ import annotations
from typing import Any, Dict, List, Optional
from dataclasses import asdict, is_dataclass
import logging
import uuid

from .inventor import generate_proposals  # returns list[StrategyProposalV1 or dict]
from decision.decision_engine import DecisionEngine  # decide(bundle, proposals, conn_str)

# ---------- helpers ----------
def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    if hasattr(obj, key):
        try:
            return getattr(obj, key)
        except Exception:
            return default
    return default

def _to_dict(obj: Any) -> Dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    # pydantic v2
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump()  # type: ignore[attr-defined]
        except Exception:
            pass
    # pydantic v1
    if hasattr(obj, "dict"):
        try:
            return obj.dict()  # type: ignore[attr-defined]
        except Exception:
            pass
    if is_dataclass(obj):
        try:
            return asdict(obj)
        except Exception:
            pass
    return {}

def _summarize_proposals(cands: List[Any], k: int = 10) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in (cands or [])[:k]:
        out.append({
            "strategy": _get(p, "strategy", _get(p, "name")),
            "intent": _get(p, "intent"),
            "qty": _get(p, "qty_raw", _get(p, "qty")),
            "score": _get(p, "risk_adjusted", _get(p, "risk_score")),
            "id": _get(p, "id"),
        })
    return out

def _fallback_size(decision: Dict[str, Any], proposals: List[Any]) -> bool:
    """size<=0 のとき、候補の qty と risk を用いて size を補完する。補完したら True。"""
    try:
        size = float(_get(decision, "size", 0) or 0.0)
    except Exception:
        size = 0.0

    if size > 0.0:
        return False

    best = proposals[0] if proposals else None
    if best is None:
        # 最低でも 1e-3 を入れて「ゼロではない」ことを担保
        decision["size"] = 1e-3
        decision["reason"] = (decision.get("reason", "") + " [fallback_size_applied(min)]").strip()
        return True

    try:
        qty = float(_get(best, "qty_raw", _get(best, "qty", 0.0)) or 0.0)
    except Exception:
        qty = 0.0
    try:
        risk = float(_get(best, "risk_adjusted", _get(best, "risk_score", 0.5)) or 0.5)
    except Exception:
        risk = 0.5

    patched = max(1e-3, qty * max(0.1, risk))
    decision["size"] = patched
    decision["reason"] = (decision.get("reason", "") + " [fallback_size_applied(qty*risk)]").strip()
    return True

# ---------- main entry ----------
def run_inventor_and_decide(
    bundle: Any,
    conn_str: Optional[str] = None,
    use_harmonia: bool = True,
) -> Dict[str, Any]:
    """
    Inventor -> (optional Harmonia rerank) -> DecisionEngine
    Returns:
      {"trace_id": str, "proposal_summary": [...], "decision": {...}}
    """
    # proposals
    proposals: List[Any] = generate_proposals(bundle)

    # optional rerank by Harmonia (dict/model 両対応)
    if use_harmonia:
        try:
            from codex.agents.harmonia import rerank_candidates  # added in our Harmonia
            ctx = _to_dict(_get(bundle, "context", {}))
            feats = _get(bundle, "features", {})
            quality = _to_dict(feats if isinstance(feats, dict) else _get(feats, "quality", {}))
            proposals = rerank_candidates(proposals, context=ctx, quality=quality)
        except Exception as e:
            logging.info("[Harmonia] Rerank skipped or failed: %r", e)

    # decide
    eng = DecisionEngine()
    record, decision = eng.decide(bundle, proposals=proposals, conn_str=conn_str)

    # normalize decision to dict (for return payload)
    d = decision if isinstance(decision, dict) else _to_dict(decision)

    # fallback size if needed（戻り値の decision は非ゼロにする）
    _fallback_size(d, proposals)

    # trace_id（bundle か decision 由来で確保。なければ生成）
    trace_id = _get(bundle, "trace_id") or _get(d, "trace_id") or str(uuid.uuid4())

    return {
        "trace_id": trace_id,
        "proposal_summary": _summarize_proposals(proposals, k=10),
        "decision": d,
    }
