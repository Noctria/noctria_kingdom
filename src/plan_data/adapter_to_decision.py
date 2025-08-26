# src/plan_data/adapter_to_decision.py
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Optional

import pandas as pd

# --- plan layer ---
from plan_data.strategy_adapter import (
    FeatureBundle,
    StrategyProposal,
    propose_with_logging,
)
from plan_data.trace import get_trace_id, new_trace_id

# --- decision layer ---
from decision.decision_engine import DecisionEngine, DecisionRequest, DecisionResult


def _pick_trace_id(features: FeatureBundle, fallback_symbol: str = "MULTI", fallback_tf: str = "1d") -> str:
    """
    trace_id の決定：
      1) features.context["trace_id"] があればそれ
      2) get_trace_id() が返るならそれ
      3) new_trace_id(symbol, timeframe)
    """
    ctx = features.context or {}
    tid = ctx.get("trace_id") or get_trace_id()
    if tid:
        return str(tid)
    return new_trace_id(
        symbol=str(ctx.get("symbol", fallback_symbol)),
        timeframe=str(ctx.get("timeframe", fallback_tf)),
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
      "decision": <DecisionResult as dict>
    }
    """
    # 1) 戦略実行（Quality Gate は adapter 内で適用済み）
    proposal = propose_with_logging(
        strategy,
        features,
        model_name=model_name,
        model_version=model_version,
        timeout_sec=timeout_sec,
        trace_id=features.context.get("trace_id"),  # あれば引き継ぎ
        conn_str=conn_str,
        **strategy_kwargs,
    )

    # 2) DecisionEngine への入力を組み立て（quality hints と base_qty を含める）
    hints = _quality_hints_from_proposal(proposal)
    dec_features: Dict[str, Any] = {
        # トレンド/ボラなど、呼び出し側で自由に足せる（なければデフォルトで判定）
        "volatility": features.context.get("volatility", 0.20),
        "trend_score": features.context.get("trend_score", 0.50),
        # quality & sizing
        **hints,
    }
    if extra_decision_features:
        dec_features.update(extra_decision_features)

    trace_id = _pick_trace_id(features)
    req = DecisionRequest(
        trace_id=trace_id,
        symbol=str(features.context.get("symbol", proposal.symbol)),
        features=dec_features,
    )

    eng = engine or DecisionEngine()
    decision = eng.decide(req, conn_str=conn_str)

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
            "strategy_name": decision.strategy_name,
            "score": decision.score,
            "reason": decision.reason,
            "decision": dict(decision.decision),
        },
        "trace_id": trace_id,
    }
    return out


# --- 手動テスト用 ---
if __name__ == "__main__":
    # 最小ダミー戦略
    class DummyStrategy:
        def propose(self, features: FeatureBundle, **kw):
            # Quality Gate（strategy_adapter 側）が SCALE を適用済みなら qty は既に縮小されている想定
            return StrategyProposal(
                symbol=str(features.context.get("symbol", "USDJPY")),
                direction="LONG",
                qty=100.0,
                confidence=0.8,
                reasons=["dummy ok"],
                meta={},  # strategy_adapter 内で quality_action/qty_scale を追加
            )

    # 特徴量（最低限）
    df = pd.DataFrame({"date": pd.date_range("2025-08-01", periods=5, freq="D")})
    fb = FeatureBundle(
        df=df,
        context={
            "symbol": "USDJPY",
            "timeframe": "1d",
            # DecisionEngine 用の判断材料（任意）
            "volatility": 0.10,
            "trend_score": 0.75,
            # Quality Gate 判定材料（strategy_adapter 内 evaluate_quality が参照）
            "data_lag_min": 0,
            "missing_ratio": 0.12,  # > 0.05 で SCALE 想定
        },
    )

    result = run_strategy_and_decide(DummyStrategy(), fb)
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
