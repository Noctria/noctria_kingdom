cat > src/plan_data/run_inventor.py <<'PY'
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import uuid4

from plan_data.inventor import generate_proposals
from codex.agents.harmonia import rerank_candidates

# --- 型ヒント（実体は別モジュール。ここでは厳密さより安全運用を優先）---
FeatureBundle = Dict[str, Any]  # {"context": {...}, "features": {...}} を想定
StrategyProposal = Any          # pydantic Model でも dict でも扱えるように

# ----------------------------------------------------------------------
# 小道具
# ----------------------------------------------------------------------
def _obj_get(o: Any, key: str, default: Any = None) -> Any:
    """dict/オブジェクトの両対応 get"""
    if isinstance(o, dict):
        return o.get(key, default)
    if hasattr(o, key):
        try:
            return getattr(o, key)
        except Exception:
            return default
    return default


def _summarize_proposals(proposals: List[StrategyProposal], k: int = 10) -> List[Dict[str, Any]]:
    """提案の概要（ログ/返却用に安全化）。pydantic/dict/任意オブジェクト両対応。"""
    out: List[Dict[str, Any]] = []
    for p in (proposals or [])[:k]:
        out.append(
            {
                "strategy": _obj_get(p, "strategy") or _obj_get(p, "name"),
                "intent": _obj_get(p, "intent"),
                "qty": _obj_get(p, "qty") or _obj_get(p, "qty_raw") or _obj_get(p, "lot"),
                "score": _obj_get(p, "risk_adjusted") or _obj_get(p, "risk_score"),
                "id": _obj_get(p, "id"),
            }
        )
    return out


def _fallback_size(decision: Dict[str, Any], proposals: List[StrategyProposal]) -> bool:
    """
    サイズが 0 のときの保険。提案の qty_raw / risk_score から最小サイズを与える。
    返り値: 適用したかどうか
    """
    try:
        size = float(decision.get("size") or 0.0)
    except Exception:
        size = 0.0

    if size > 0:
        return False

    # 提案から最小限のサイズを拾う
    best = proposals[0] if proposals else None
    if not best:
        decision["size"] = 0.01  # 本当に何も無い最終保険
        decision["reason"] = (decision.get("reason") or "") + " fallback_size_applied:min"
        return True

    qty = _obj_get(best, "qty_raw", 0.0) or _obj_get(best, "qty", 0.0)
    try:
        qty = float(qty or 0.0)
    except Exception:
        qty = 0.0

    if qty <= 0:
        risk = _obj_get(best, "risk_score", 0.5) or 0.5
        try:
            risk = float(risk)
        except Exception:
            risk = 0.5
        qty = max(0.01, 0.1 * risk)

    decision["size"] = float(qty)
    decision["reason"] = (decision.get("reason") or "") + " fallback_size_applied"
    return True


def _ensure_bundle(fb: Optional[FeatureBundle]) -> FeatureBundle:
    """
    FeatureBundle を安全に用意する。
    - **FeatureContext のような型（= Any エイリアスの可能性がある）を new しない**
    - dict で構築し、下流(pydantic)側にパースを任せる
    """
    if not fb:
        fb = {}
    context = dict(_obj_get(fb, "context", {}) or {})
    features = dict(_obj_get(fb, "features", {}) or {})

    # デフォルト文脈
    symbol = context.get("symbol") or "USDJPY"
    timeframe = context.get("timeframe") or "M15"
    context.setdefault("symbol", symbol)
    context.setdefault("timeframe", timeframe)
    context.setdefault("data_lag_min", int(features.get("data_lag_min", 0) or 0))
    context.setdefault("missing_ratio", float(features.get("missing_ratio", 0.0) or 0.0))

    return {"context": context, "features": features}


# ----------------------------------------------------------------------
# メイン
# ----------------------------------------------------------------------
def run_inventor_and_decide(
    fb: Optional[FeatureBundle] = None,
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
) -> Dict[str, Any]:
    """
    1) Inventor で提案群を生成
    2) Harmonia で簡易リランク
    3) 最良案から意思決定オブジェクトを合成（size=0 の場合は保険で埋める）
    """
    trace_id = str(uuid4())
    bundle = _ensure_bundle(fb)

    # 呼び出し引数で context を上書き可能に
    if symbol:
        bundle["context"]["symbol"] = symbol
    if timeframe:
        bundle["context"]["timeframe"] = timeframe

    # 1) 提案生成（pydantic/dict どちらでも返ってOK）
    proposals: List[StrategyProposal] = generate_proposals(bundle)

    # 2) 簡易リランク（品質と文脈を与える）
    quality = {
        "missing_ratio": float(bundle["context"].get("missing_ratio", 0.0) or 0.0),
        "data_lag_min": float(bundle["context"].get("data_lag_min", 0.0) or 0.0),
    }
    ranked: List[StrategyProposal] = rerank_candidates(
        proposals,
        context=bundle.get("context"),
        quality=quality,
    )
    best = ranked[0] if ranked else None

    # 3) 意思決定オブジェクトを合成
    strategy_name = None
    if best is not None:
        strategy_name = _obj_get(best, "strategy") or _obj_get(best, "name")

    decision: Dict[str, Any] = {
        "action": "BUY",  # MVP: buy_simple 固定
        "symbol": bundle["context"].get("symbol", "USDJPY"),
        "size": float(_obj_get(best, "qty_raw", 0.0) or 0.0),
        "proposal": {
            "strategy": strategy_name or f"inventor/buy_simple@{bundle['context']['symbol']}-{bundle['context']['timeframe']}",
            "side": "BUY",
            "risk_score": _obj_get(best, "risk_adjusted", _obj_get(best, "risk_score", 0.5)),
        },
    }

    # size=0 のときは保険で埋める
    _fallback_size(decision, ranked)

    # 返り値（DAG側表示用）
    return {
        "trace_id": trace_id,
        "proposal_summary": _summarize_proposals(ranked, k=10),
        "decision": decision,
    }
