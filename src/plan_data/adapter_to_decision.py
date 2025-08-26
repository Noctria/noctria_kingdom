# src/plan_data/adapter_to_decision.py
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

# --- plan layer ---
from plan_data.strategy_adapter import (
    FeatureBundle,
    StrategyProposal,
    propose_with_logging,
)
from plan_data.trace import get_trace_id, new_trace_id
from plan_data.quality_gate import evaluate_quality, QualityResult

# --- decision layer ---
from decision.decision_engine import DecisionEngine, DecisionRequest, DecisionResult


# ==============================
# 内部ユーティリティ
# ==============================
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


def _safe_series(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def _derive_decision_features(df: pd.DataFrame) -> Dict[str, float]:
    """
    DecisionEngine 最小入力（volatility, trend_score）を DF から推定。
      - volatility: 日次リターンの 20 期間標準偏差（HV20）
      - trend_score: 30 期間 Sharpe を -1.5..+1.5 → 0..1 に線形射影
    """
    if df is None or df.empty:
        return {"volatility": 0.20, "trend_score": 0.50}

    df = df.copy()

    # リターン系列の用意
    if "kpi_ret" in df.columns:
        ret = _safe_series(df["kpi_ret"])
    else:
        close_cols = [c for c in df.columns if isinstance(c, str) and c.endswith("_close")]
        if not close_cols:
            return {"volatility": 0.20, "trend_score": 0.50}
        price = _safe_series(df[close_cols[0]])
        ret = price.pct_change()

    hv20 = float(ret.rolling(window=20, min_periods=10).std().iloc[-1])
    mu = ret.rolling(window=30, min_periods=10).mean()
    sd = ret.rolling(window=30, min_periods=10).std().replace(0.0, np.nan)
    sharpe_30 = (mu / sd) * math.sqrt(252)
    sh = float(sharpe_30.iloc[-1]) if not sharpe_30.empty else 0.0
    trend_score = (max(-1.5, min(1.5, sh)) + 1.5) / 3.0  # → 0..1

    # NaN/inf 防御
    if math.isnan(hv20) or math.isinf(hv20):
        hv20 = 0.20
    if math.isnan(trend_score) or math.isinf(trend_score):
        trend_score = 0.50

    return {"volatility": hv20, "trend_score": trend_score}


def _apply_quality_to_proposal(q: QualityResult, p: StrategyProposal) -> StrategyProposal:
    """
    QualityGate の出力に従って提案を補正。
      - action == "FLAT" → FLAT/qty=0
      - action == "SCALE" → qty *= qty_scale
      - action == "OK" → そのまま
    meta に quality 情報を埋め込み（GUI/ログで利用）
    """
    meta = dict(p.meta or {})
    meta.update(
        {
            "quality_action": q.action,
            "qty_scale": float(q.qty_scale),
            "quality_reasons": list(q.reasons or []),
        }
    )

    if q.action == "FLAT":
        return StrategyProposal(
            symbol=p.symbol,
            direction="FLAT",
            qty=0.0,
            confidence=min(float(p.confidence), 0.5),
            reasons=[*list(p.reasons or []), "quality:FLAT"],
            meta=meta,
            schema_version=p.schema_version,
        )
    if q.action == "SCALE":
        scaled = max(0.0, float(p.qty) * float(q.qty_scale))
        return StrategyProposal(
            symbol=p.symbol,
            direction=p.direction,
            qty=scaled,
            confidence=float(p.confidence),
            reasons=[*list(p.reasons or []), f"quality:SCALE x{q.qty_scale:.2f}"],
            meta=meta,
            schema_version=p.schema_version,
        )
    # OK
    meta.setdefault("quality_action", "OK")
    meta.setdefault("qty_scale", 1.0)
    return StrategyProposal(
        symbol=p.symbol,
        direction=p.direction,
        qty=float(p.qty),
        confidence=float(p.confidence),
        reasons=list(p.reasons or []),
        meta=meta,
        schema_version=p.schema_version,
    )


# ==============================
# Public API
# ==============================
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
    quality_max_lag_min: int = 30,
    quality_max_missing: float = 0.05,
    **strategy_kwargs: Any,
) -> Dict[str, Any]:
    """
    1) strategy_adapter.propose_with_logging(...) で戦略実行（obs_infer_calls に計測）
    2) QualityGate をここで適用（数量スケール/強制FLAT）
    3) DecisionEngine.decide(...) を呼び、結果を dict で返す（提案も同梱）

    戻り値:
    {
      "proposal": {...},           # Quality 適用済み
      "decision": {...},
      "trace_id": "<id>",
      "quality": {"action": "...", "qty_scale": 1.0, "reasons": [...]},
      "decision_features": {"volatility": ..., "trend_score": ... , ...}
    }
    """
    # 1) 戦略実行（ここでは品質調整はまだ）
    proposal_raw = propose_with_logging(
        strategy,
        features,
        model_name=model_name,
        model_version=model_version,
        timeout_sec=timeout_sec,
        trace_id=features.context.get("trace_id"),  # あれば引き継ぎ
        conn_str=conn_str,
        **strategy_kwargs,
    )

    # 2) QualityGate（features.context の data_lag_min / missing_ratio を参照）
    qres = evaluate_quality(
        features,
        max_lag_min=int(quality_max_lag_min),
        max_missing=float(quality_max_missing),
    )
    proposal = _apply_quality_to_proposal(qres, proposal_raw)

    # 3) DecisionEngine 入力（DFから最小特徴を推定し、extraで上書き可能）
    dec_feats = _derive_decision_features(features.df)
    if extra_decision_features:
        dec_feats.update(extra_decision_features)

    trace_id = _pick_trace_id(features)
    req = DecisionRequest(
        trace_id=trace_id,
        symbol=str(features.context.get("symbol", proposal.symbol)),
        features=dec_feats,
    )
    eng = engine or DecisionEngine()
    decision: DecisionResult = eng.decide(req, conn_str=conn_str)

    # 4) まとめて返す
    out = {
        "proposal": {
            "symbol": proposal.symbol,
            "direction": proposal.direction,
            "qty": float(proposal.qty),
            "confidence": float(proposal.confidence),
            "reasons": list(proposal.reasons or []),
            "meta": dict(proposal.meta or {}),
            "schema_version": str(proposal.schema_version),
        },
        "decision": {
            "strategy_name": decision.strategy_name,
            "score": float(decision.score),
            "reason": decision.reason,
            "decision": dict(decision.decision),
        },
        "trace_id": trace_id,
        "quality": {
            "action": qres.action,
            "qty_scale": float(qres.qty_scale),
            "reasons": list(qres.reasons or []),
        },
        "decision_features": dec_feats,
    }
    return out


__all__ = ["run_strategy_and_decide"]
