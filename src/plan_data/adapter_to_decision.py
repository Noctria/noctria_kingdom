# src/plan_data/adapter_to_decision.py
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Optional

import pandas as pd

# ---- plan layer imports（相対/絶対 両対応。※自分自身は絶対に import しない）----
try:
    from plan_data.strategy_adapter import (
        FeatureBundle,
        StrategyProposal,
        propose_with_logging,
    )  # type: ignore
    from plan_data.trace import get_trace_id, new_trace_id  # type: ignore
except Exception:
    from src.plan_data.strategy_adapter import (  # type: ignore
        FeatureBundle,
        StrategyProposal,
        propose_with_logging,
    )
    from src.plan_data.trace import get_trace_id, new_trace_id  # type: ignore

# ---- decision layer ----
# ※ ここは contracts からではなく decision.decision_engine から！
try:
    from decision.decision_engine import (  # type: ignore
        DecisionEngine,
    )
except Exception:
    from src.decision.decision_engine import (  # type: ignore
        DecisionEngine,
    )


def _pick_trace_id(features: FeatureBundle, fallback_symbol: str = "MULTI", fallback_tf: str = "1d") -> str:
    """
    trace_id の決定：
      1) features.context.trace_id があればそれ
      2) get_trace_id() が返るならそれ
      3) new_trace_id(symbol, timeframe)
    """
    ctx = getattr(features, "context", None)
    tid = getattr(ctx, "trace_id", None) or get_trace_id()
    if tid:
        return str(tid)
    return new_trace_id(
        symbol=str(getattr(ctx, "symbol", fallback_symbol)),
        timeframe=str(getattr(ctx, "timeframe", fallback_tf)),
    )


def _quality_hints_from_proposal(p: StrategyProposal) -> Dict[str, Any]:
    """
    strategy_adapter 側で付与した meta から quality 情報を抽出。
    - quality_action: "OK" | "SCALE" | "FLAT"（無ければ "OK"）
    - qty_scale:      float（無ければ 1.0）
    - base_qty:       提案数量（float）
    """
    meta = dict(p.meta or {})
    qa = str(meta.get("quality_action", "OK")).upper()
    try:
        qs = float(meta.get("qty_scale", 1.0))
    except Exception:
        qs = 1.0

    try:
        bq = float(p.qty)
    except Exception:
        bq = 0.0

    return {"quality_action": qa, "qty_scale": qs, "base_qty": bq}


def run_strategy_and_decide(
    strategy: Any,
    features: FeatureBundle,
    *,
    engine: Optional[DecisionEngine] = None,
    model_name: Optional[str] = None,
    model_version: Optional[str] = None,
    timeout_sec: Optional[float] = None,
    conn_str: Optional[str] = None,
    extra_decision_features: Optional[Dict[str, Any]] = None,
    **strategy_kwargs: Any,
) -> Dict[str, Any]:
    """
    1) plan_data.strategy_adapter.propose_with_logging(...) で戦略を実行
    2) Proposal の quality 情報を DecisionEngine に橋渡し
    3) DecisionEngine.decide(...) を呼び、結果を dict で返す（提案も同梱）

    戻り値:
    {
      "proposal": <StrategyProposal as dict>,
      "decision": <DecisionRecord + decision dict> の一部を抜粋,
      "trace_id": "<id>"
    }
    """
    # 1) 戦略実行（Quality Gate は adapter 内で適用済み）
    proposal = propose_with_logging(
        strategy,
        features,
        model_name=model_name,
        model_version=model_version,
        timeout_sec=timeout_sec,
        trace_id=getattr(features.context, "trace_id", None),  # ← 修正
        conn_str=conn_str,
        **strategy_kwargs,
    )

    # 2) DecisionEngine への入力（DecisionEngine は proposals のリストを受ける設計）
    eng = engine or DecisionEngine()
    record, decision = eng.decide(features, proposals=[proposal], conn_str=conn_str)

    # 3) まとめて返す（扱いやすい dict 形式）
    out = {
        "proposal": {
            "symbol": proposal.symbol,
            "direction": proposal.direction,
            "qty": proposal.qty,
            "confidence": proposal.confidence,
            "reasons": list(proposal.reasons or []),
            "meta": dict(proposal.meta or {}),
            "schema_version": proposal.schema_version,
        },
        "decision": {
            "strategy_name": record.strategy_name,
            "score": record.score,
            "reason": record.reason,
            "decision": dict(decision),
        },
        "trace_id": record.trace_id,
    }
    return out


# --- 手動テスト用（任意） ---
if __name__ == "__main__":
    class DummyStrategy:
        def propose(self, features: FeatureBundle, **kw):
            return StrategyProposal(
                symbol=str(getattr(features.context, "symbol", "USDJPY")),
                direction="LONG",
                qty=100.0,
                confidence=0.8,
                reasons=["dummy ok"],
                meta={},
            )

    df = pd.DataFrame({"date": pd.date_range("2025-08-01", periods=5, freq="D")})
    fb = FeatureBundle(
        features=df,
        trace_id="manual-trace-001",
        context={
            "symbol": "USDJPY",
            "timeframe": "1d",
            "data_lag_min": 0,
            "missing_ratio": 0.0,
        },
    )
    result = run_strategy_and_decide(DummyStrategy(), fb)
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
