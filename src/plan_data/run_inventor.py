# src/plan_data/run_inventor.py
from __future__ import annotations
from typing import Any, Dict, List, Optional

def run_inventor_and_decide(
    fb, *,
    max_n: int = 3,
    default_lot: float = 0.5,
    conn_str: Optional[str] = None,
    use_harmonia: bool = True,
) -> Dict[str, Any]:
    """
    - Inventor で候補生成 → （任意で Harmonia で rerank）→ DecisionEngine で決定
    - 返却は Airflow XCom/GUI で扱いやすい軽い dict
    """
    # 遅延 import（DAG パースを軽く・循環防止）
    from plan_data import inventor
    from decision.decision_engine import DecisionEngine  # type: ignore
    from plan_data.observability import emit_alert, log_infer_call  # type: ignore

    # 候補生成（エラー時は inventor.generate_proposals_safe が空配列を返す）
    cands = inventor.generate_proposals_safe(fb, max_n=max_n, default_lot=default_lot)

    # （任意）Harmonia rerank
    if use_harmonia and cands:
        try:
            # 軽い依存にするため遅延 import + 失敗は握りつぶす
            from codex.agents.harmonia import rerank_candidates  # type: ignore
            cands = rerank_candidates(cands) or cands
        except Exception:
            # rerank 失敗は重大ではないので無視（観測だけ入れる）
            try:
                emit_alert(
                    kind="HARMONIA.SKIP",
                    reason="rerank failed or module missing",
                    severity="LOW",
                    trace=getattr(getattr(fb, "context", None), "trace_id", None),
                    details={},
                    conn_str=conn_str,
                )
            except Exception:
                pass

    # DecisionEngine で最終決定
    eng = DecisionEngine()
    record, decision = eng.decide(fb, proposals=cands, conn_str=conn_str)

    # 観測（軽量）
    try:
        log_infer_call(
            provider="inventor",
            model="inventor_v1+harmonia" if use_harmonia else "inventor_v1",
            prompt={"symbol": getattr(getattr(fb, "context", None), "symbol", None)},
            response={"num_candidates": len(cands)},
            latency_ms=0,
            conn_str=conn_str,
        )
    except Exception:
        pass

    # Airflow/GUI に載せやすい形で返す
    return {
        "trace_id": record.trace_id,
        "proposal_summary": [
            {
                "name": getattr(p, "name", None),
                "action": getattr(p, "action", None),
                "lot": getattr(p, "lot", None),
                "score": getattr(p, "score", None),
                "risk_score": getattr(p, "risk_score", None),
                "symbol": getattr(p, "symbol", None),
            }
            for p in (cands or [])
        ],
        "decision": {
            "strategy_name": record.strategy_name,
            "score": record.score,
            "reason": record.reason,
            "decision": dict(decision),
        },
    }
