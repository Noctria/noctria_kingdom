# src/plan_data/run_inventor.py
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# 軽量依存のみ
try:
    from plan_data import inventor as inventor_mod  # repo構成に合わせて相対/絶対
except Exception:
    from . import inventor as inventor_mod  # fallback

try:
    from codex.agents import harmonia as harmonia_mod
except Exception:
    # ローカル実行時の簡易相対
    from ...codex.agents import harmonia as harmonia_mod  # type: ignore

LOGGER = logging.getLogger("airflow.task")

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _make_trace_id() -> str:
    return f"invharm-{uuid.uuid4().hex[:12]}"

def _fallback_size(decision: Dict[str, Any], ranked: List[Any]) -> bool:
    """
    size==0 の場合のフォールバック。
    - qty_raw / risk_score を使って最小ロットを決める簡易実装（重依存なし）
    """
    try:
        if (decision.get("size") or 0) > 0:
            return False
        top = ranked[0] if ranked else None
        qty_raw = getattr(top, "qty_raw", None) if top else None
        risk_score = getattr(top, "risk_score", None) if top else None

        base = 0.01  # 最小ロットのベース
        bump = 0.0
        if isinstance(qty_raw, (int, float)):
            bump += float(qty_raw) * 0.001
        if isinstance(risk_score, (int, float)):
            bump += max(0.0, min(float(risk_score), 1.0)) * 0.02

        size = round(base + bump, 3)
        if size <= 0:
            size = base
        decision["size"] = size
        decision["reason"] = (decision.get("reason") or "") + " | fallback:size"
        return True
    except Exception as e:
        LOGGER.warning("fallback_size failed: %s", e)
        return False

def _decision_from_ranked(ranked: List[Any]) -> Dict[str, Any]:
    """
    最上位提案から超軽量の意思決定を作る。
    """
    if not ranked:
        return {"side": "FLAT", "size": 0.0, "reason": "no_proposals"}
    top = ranked[0]
    side = getattr(top, "intent", "BUY")
    if side not in ("BUY", "SELL"):
        side = "BUY"
    # 初期は 0（フォールバックで上書き想定）
    return {"side": side, "size": 0.0, "reason": "ranked_top"}

def run_inventor_and_decide(bundle: Optional[Dict[str, Any]] = None, **_) -> Dict[str, Any]:
    """
    軽量E2E：Inventor -> Harmonia -> Decision
    - bundle: {"context": {"symbol": "...", "timeframe": "...", ...}, ...}
    - 余剰kwargsは受け流し（DAGパラメータの互換確保）
    """
    bundle = bundle or {}
    context = dict(bundle.get("context") or {})
    symbol = context.get("symbol") or "USDJPY"
    timeframe = context.get("timeframe") or "M15"
    trace_id = context.get("trace_id") or _make_trace_id()
    context.update({"symbol": symbol, "timeframe": timeframe, "trace_id": trace_id})

    # 1) Inventor 提案生成
    proposals = inventor_mod.generate_proposals(context=context)

    # 2) Harmonia リランク（risk_adjustedなど簡易重み付け）
    ranked = harmonia_mod.rerank_candidates(proposals, context=context)

    # 3) Decision（size はフォールバックで最終確定）
    decision = _decision_from_ranked(ranked)
    applied = _fallback_size(decision, ranked)

    # 観測ログ（Airflow ロガー）
    LOGGER.info(
        "[Harmonia] reranked %s -> %s top=%s symbol=%s tf=%s trace=%s",
        len(proposals or []),
        len(ranked or []),
        (getattr(ranked[0], "intent", None) if ranked else None),
        symbol,
        timeframe,
        trace_id,
    )
    if applied:
        LOGGER.info("[Decision] fallback_size_applied size=%s trace=%s", decision["size"], trace_id)

    # 返却（XCom軽量化のため dict のみ）
    result = {
        "trace_id": trace_id,
        "context": {"symbol": symbol, "timeframe": timeframe},
        "decision": decision,
        "meta": {
            "created_at": _now_iso(),
            "ranked_top_quality": getattr(ranked[0], "quality", None) if ranked else None,
        },
    }
    # デバッグ用に1行 JSON （Airflowログで見やすく）
    LOGGER.info("Returned value was: %s", json.dumps(result, ensure_ascii=False))
    return result
