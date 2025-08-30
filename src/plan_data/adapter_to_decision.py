# src/plan_data/adapter_to_decision.py
from __future__ import annotations

from typing import Any, Dict, Optional
import pandas as pd
import json

# Pydanticモデルを直接インポートするように修正
# try-exceptブロックはライブラリの安定性に応じて調整
from .contracts import (
    FeatureBundle,
    StrategyProposal,
    DecisionEngine,
    DecisionRequest,
    DecisionResult,
)
from .strategy_adapter import propose_with_logging
from .trace import get_trace_id, new_trace_id
from . import quality_gate
from . import noctus_gate
from . import observability


def _pick_trace_id(features: FeatureBundle) -> str:
    """
    trace_id を決定する新しいロジック
    1) features.trace_id があれば最優先
    2) get_trace_id() があればそれを利用
    3) 上記がなければ、context情報から新しいIDを生成
    """
    if features.trace_id:
        return features.trace_id
    
    tid = get_trace_id()
    if tid:
        return str(tid)
        
    symbol = getattr(features.context, "symbol", "MULTI")
    timeframe = getattr(features.context, "timeframe", "1d")
    return new_trace_id(symbol=str(symbol), timeframe=str(timeframe))


def _quality_hints_from_proposal(p: StrategyProposal) -> Dict[str, Any]:
    """
    strategy_adapter 側で付与した meta から quality 情報を抽出。
    Pydanticモデル対応のため getattr を使用して安全にアクセス。
    """
    meta = getattr(p, "meta", {}) or {}
    qa = str(meta.get("quality_action", "OK")).upper()
    
    try:
        qs = float(meta.get("qty_scale", 1.0))
    except (ValueError, TypeError):
        qs = 1.0

    base_qty = getattr(p, "qty", getattr(p, "lot", getattr(p, "size", 0.0)))
    
    try:
        bq = float(base_qty or 0.0)
    except (ValueError, TypeError):
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
    1) QualityGate を評価
    2) 戦略を実行
    3) NoctusGate で提案をチェック
    4) DecisionEngine で最終判断
    """
    trace_id = _pick_trace_id(features)

    # 1) QualityGate
    _ = quality_gate.evaluate_quality(features, conn_str=conn_str)

    # 2) 戦略実行
    proposal = propose_with_logging(
        strategy,
        features,
        model_name=model_name,
        model_version=model_version,
        timeout_sec=timeout_sec,
        trace_id=trace_id,  # --- 修正点: 正しいtrace_idを引き継ぎ ---
        conn_str=conn_str,
        **strategy_kwargs,
    )

    # 3) NoctusGate: プレ実行リスクチェック
    ng = noctus_gate.check_proposal(proposal, conn_str=conn_str)
    if not ng.ok:
        # ブロック時は REJECT を返す
        symbol = getattr(proposal, "symbol", features.context.symbol)
        qty = getattr(proposal, "qty", 0.0)
        
        return {
            "proposal": proposal.dict(),
            "decision": {
                "strategy_name": "blocked_by_noctus",
                "score": 0.0,
                "reason": "NoctusGate blocked: " + "; ".join(ng.reasons),
                "decision": {
                    "action": "REJECT",
                    "symbol": symbol,
                    "size": float(qty or 0.0),
                },
            },
            "trace_id": trace_id,
        }

    # 4) DecisionEngine の判断
    hints = _quality_hints_from_proposal(proposal)
    dec_features: Dict[str, Any] = {
        # --- 修正点: getattrで安全にオプショナルな属性にアクセス ---
        "volatility": getattr(features.context, "volatility", 0.20),
        "trend_score": getattr(features.context, "trend_score", 0.50),
        **hints,
    }
    if extra_decision_features:
        dec_features.update(extra_decision_features)

    req = DecisionRequest(
        trace_id=trace_id,
        symbol=str(getattr(features.context, "symbol", proposal.symbol)),
        features=dec_features,
    )

    eng = engine or DecisionEngine()
    decision = eng.decide(req, conn_str=conn_str)

    # 5) まとめて返す
    return {
        "proposal": proposal.dict(),
        "decision": decision.dict(),
        "trace_id": trace_id,
    }


# --- 手動テスト用 ---
if __name__ == "__main__":
    
    class DummyStrategy:
        def propose(self, features: FeatureBundle, **kw):
            return StrategyProposal(
                symbol=str(features.context.symbol),
                direction="LONG",
                qty=100.0,
                confidence=0.8,
                reasons=["dummy ok"],
                meta={},
            )

    df = pd.DataFrame({"date": pd.to_datetime(["2025-08-01", "2025-08-02"])})
    
    # --- 修正点: Pydanticモデルに合わせてFeatureBundleを作成 ---
    fb = FeatureBundle(
        features=df,
        trace_id="manual-test-trace-001",
        context={
            "symbol": "USDJPY",
            "timeframe": "1d",
            "volatility": 0.10,
            "trend_score": 0.75,
            "data_lag_min": 0,
            "missing_ratio": 0.12,
        },
    )

    result = run_strategy_and_decide(DummyStrategy(), fb)
    print(json.dumps(result, indent=2, ensure_ascii=False))
