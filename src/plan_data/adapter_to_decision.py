# src/plan_data/adapter_to_decision.py
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Optional

import pandas as pd

# ---- plan layer imports（相対/絶対 両対応）----
try:
    from plan_data.strategy_adapter import (
        FeatureBundle,
        StrategyProposal,
        propose_with_logging,
    )  # type: ignore
    from plan_data.trace import get_trace_id, new_trace_id  # type: ignore
    from plan_data import quality_gate  # type: ignore
    from plan_data import noctus_gate   # type: ignore
    from plan_data import observability # type: ignore
except Exception:
    from src.plan_data.strategy_adapter import (  # type: ignore
        FeatureBundle,
        StrategyProposal,
        propose_with_logging,
    )
    from src.plan_data.trace import get_trace_id, new_trace_id  # type: ignore
    from src.plan_data import quality_gate  # type: ignore
    from src.plan_data import noctus_gate   # type: ignore
    from src.plan_data import observability # type: ignore

# ---- decision layer ----
try:
    from decision.decision_engine import (  # type: ignore
        DecisionEngine,
        DecisionRequest,
        DecisionResult,
    )
except Exception:
    from src.decision.decision_engine import (  # type: ignore
        DecisionEngine,
        DecisionRequest,
        DecisionResult,
    )


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
    meta = dict(getattr(p, "meta", {}) or (p.get("meta") if isinstance(p, dict) else {}) or {})
    qa = str(meta.get("quality_action", "OK")).upper()
    try:
        qs = float(meta.get("qty_scale", 1.0))
    except Exception:
        qs = 1.0

    base_qty = None
    # オブジェクト or dict の両対応
    if isinstance(p, dict):
        base_qty = p.get("qty") or p.get("lot") or p.get("size") or 0.0
    else:
        base_qty = getattr(p, "qty", getattr(p, "lot", getattr(p, "size", 0.0)))

    try:
        bq = float(base_qty or 0.0)
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
    1) QualityGate を先に評価（品質異常は obs_alerts に自動記録）
    2) plan_data.strategy_adapter.propose_with_logging(...) で戦略を実行（obs_infer_calls に記録）
    3) NoctusGate で提案を即チェック。違反は REJECT を返す（obs_alerts に自動記録）
    4) DecisionEngine.decide(...) を呼び、結果を dict で返す（提案も同梱）

    戻り値:
    {
      "proposal": <StrategyProposal as dict>,
      "decision": {
        "strategy_name": ...,
        "score": ...,
        "reason": ...,
        "decision": {...}
      },
      "trace_id": "<id>"
    }
    """
    # 1) QualityGate（可観測: quality_gate 内で emit_alert 済み）
    _ = quality_gate.evaluate_quality(features, conn_str=conn_str)

    # 2) 戦略実行（Quality Gate による SCALE/FLAT は adapter 内で適用されている想定）
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

    # 3) NoctusGate: プレ実行リスクチェック（lot/size, risk_score など）
    ng = noctus_gate.check_proposal(proposal, conn_str=conn_str)
    if not ng.ok:
        # ブロック時は REJECT を返す（DecisionEngine を呼ばず即返却）
        symbol = (
            proposal.get("symbol")
            if isinstance(proposal, dict)
            else getattr(proposal, "symbol", features.context.get("symbol", "USDJPY"))
        )
        qty = (
            proposal.get("qty") or proposal.get("lot") or proposal.get("size") or 0.0
            if isinstance(proposal, dict)
            else getattr(proposal, "qty", getattr(proposal, "lot", getattr(proposal, "size", 0.0)))
        )
        try:
            qty = float(qty or 0.0)
        except Exception:
            qty = 0.0

        # 出力形式は通常時と同じ dict 形式を維持
        out = {
            "proposal": {
                "symbol": symbol,
                "direction": (
                    proposal.get("direction") if isinstance(proposal, dict)
                    else getattr(proposal, "direction", None)
                ),
                "qty": qty,
                "confidence": (
                    proposal.get("confidence") if isinstance(proposal, dict)
                    else getattr(proposal, "confidence", None)
                ),
                "reasons": list((proposal.get("reasons") if isinstance(proposal, dict) else getattr(proposal, "reasons", [])) or []),
                "meta": dict((proposal.get("meta") if isinstance(proposal, dict) else getattr(proposal, "meta", {})) or {}),
                "schema_version": (
                    proposal.get("schema_version") if isinstance(proposal, dict)
                    else getattr(proposal, "schema_version", None)
                ),
            },
            "decision": {
                "strategy_name": "blocked_by_noctus",
                "score": 0.0,
                "reason": "NoctusGate blocked: " + "; ".join(ng.reasons),
                "decision": {
                    "action": "REJECT",
                    "symbol": symbol,
                    "size": qty,
                    "proposal": out if False else {},  # 参照循環を避けるため proposal 本体は省略
                },
            },
            "trace_id": _pick_trace_id(features),
        }
        return out

    # 4) DecisionEngine の判断
    hints = _quality_hints_from_proposal(proposal)
    dec_features: Dict[str, Any] = {
        # 呼び出し側で自由に追加される可能性があるので、context のデフォルトを尊重
        "volatility": features.context.get("volatility", 0.20),
        "trend_score": features.context.get("trend_score", 0.50),
        # quality & sizing hints
        **hints,
    }
    if extra_decision_features:
        dec_features.update(extra_decision_features)

    trace_id = _pick_trace_id(features)
    req = DecisionRequest(
        trace_id=trace_id,
        symbol=str(features.context.get("symbol", getattr(proposal, "symbol", "USDJPY"))),
        features=dec_features,
    )

    eng = engine or DecisionEngine()
    decision = eng.decide(req, conn_str=conn_str)

    # 5) まとめて返す（扱いやすい dict 形式）
    out = {
        "proposal": {
            "symbol": (
                proposal.get("symbol")
                if isinstance(proposal, dict)
                else getattr(proposal, "symbol", features.context.get("symbol", "USDJPY"))
            ),
            "direction": (
                proposal.get("direction") if isinstance(proposal, dict)
                else getattr(proposal, "direction", None)
            ),
            "qty": (
                proposal.get("qty") or proposal.get("lot") or proposal.get("size")
                if isinstance(proposal, dict)
                else getattr(proposal, "qty", getattr(proposal, "lot", getattr(proposal, "size", None)))
            ),
            "confidence": (
                proposal.get("confidence") if isinstance(proposal, dict)
                else getattr(proposal, "confidence", None)
            ),
            "reasons": list((proposal.get("reasons") if isinstance(proposal, dict) else getattr(proposal, "reasons", [])) or []),
            "meta": dict((proposal.get("meta") if isinstance(proposal, dict) else getattr(proposal, "meta", {})) or {}),
            "schema_version": (
                proposal.get("schema_version") if isinstance(proposal, dict)
                else getattr(proposal, "schema_version", None)
            ),
        },
        "decision": {
            "strategy_name": getattr(decision, "strategy_name", None),
            "score": getattr(decision, "score", None),
            "reason": getattr(decision, "reason", ""),
            "decision": dict(getattr(decision, "decision", {}) or {}),
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
            "missing_ratio": 0.12,  # > 0.05 で SCALE 想定（quality_gate 側で ALERT も出る）
        },
    )

    result = run_strategy_and_decide(DummyStrategy(), fb)
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
