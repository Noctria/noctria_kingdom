# src/plan_data/inventor.py
from __future__ import annotations

from dataclasses import asdict
from typing import List, Optional, Any
import math
import time

from .contracts import FeatureBundle, StrategyProposal  # type: ignore
from . import observability


def _safe_get(ctx: Any, key: str, default: Any = None) -> Any:
    if ctx is None:
        return default
    if isinstance(ctx, dict):
        return ctx.get(key, default)
    return getattr(ctx, key, default)


def _simple_score_from_df(fb: FeatureBundle) -> float:
    """
    極めて軽量なスコア計算:
    - df があれば行数と時系列のspreadっぽいものから 0.4〜0.8 の範囲で決める
    - df が無ければ 0.5
    これはあくまでスモーク用（本実装ではきちんと差し替える）
    """
    df = getattr(fb, "df", None)
    if df is None or len(df) == 0:
        return 0.5
    n = max(len(df), 1)
    # 疑似ボラ = 行数の平方根でスコアに微調整
    base = 0.5 + min(0.3, 0.1 * math.log10(n + 9))
    return float(max(0.4, min(0.8, base)))


def generate_proposals(
    fb: FeatureBundle,
    *,
    max_n: int = 3,
    default_lot: float = 0.5,
) -> List[StrategyProposal]:
    """
    最小の戦略候補ジェネレーター（スモーク版）
      - BUY/SELL の2案 + 任意で HOLD 1案を返す
      - score は df からの簡易指標で 0.4〜0.8 に収める
      - risk_score は仮で score と同値（NoctusGateの動作確認に十分）
    """
    t0 = time.time()
    ctx = getattr(fb, "context", None)
    symbol = _safe_get(ctx, "symbol", "USDJPY")
    trace = _safe_get(ctx, "trace", _safe_get(ctx, "trace_id", None))
    timeframe = _safe_get(ctx, "timeframe", "1h")

    # 簡易スコア
    s = _simple_score_from_df(fb)

    # 生成（最小限のフィールドのみ埋める）
    cands: List[StrategyProposal] = []
    cands.append(
        StrategyProposal(
            name="inventor/buy_simple",
            action="BUY",
            lot=default_lot,
            score=s,
            risk_score=s,
            symbol=symbol,
            extra={"timeframe": timeframe, "generator": "inventor_v1"},
        )
    )
    cands.append(
        StrategyProposal(
            name="inventor/sell_simple",
            action="SELL",
            lot=default_lot,
            score=max(0.0, 0.9 * s),
            risk_score=max(0.0, 0.9 * s),
            symbol=symbol,
            extra={"timeframe": timeframe, "generator": "inventor_v1"},
        )
    )
    if max_n >= 3:
        cands.append(
            StrategyProposal(
                name="inventor/hold_simple",
                action="HOLD",
                lot=0.0,
                score=0.4,
                risk_score=0.4,
                symbol=symbol,
                extra={"timeframe": timeframe, "generator": "inventor_v1"},
            )
        )

    # 観測: 推論ログ（候補数など）
    try:
        observability.log_infer_call(
            provider="inventor",
            model="inventor_v1",
            prompt={"trace": trace, "symbol": symbol, "timeframe": timeframe},
            response={"num_candidates": len(cands), "scores": [p.score for p in cands]},
            latency_ms=int((time.time() - t0) * 1000),
            conn_str=None,
        )
    except Exception:
        # ログ失敗は握りつぶしてOK（本体処理は続行）
        pass

    return cands


def generate_proposals_safe(
    fb: FeatureBundle, *, max_n: int = 3, default_lot: float = 0.5
) -> List[StrategyProposal]:
    """
    失敗時も落とさない安全ラッパー。例外時は ALERT を出して空配列を返す。
    """
    ctx = getattr(fb, "context", None)
    trace = _safe_get(ctx, "trace", _safe_get(ctx, "trace_id", None))
    try:
        return generate_proposals(fb, max_n=max_n, default_lot=default_lot)
    except Exception as e:
        try:
            observability.emit_alert(
                kind="INVENTOR.ERROR",
                reason=str(e),
                severity="HIGH",
                trace=trace,
                details={"where": "generate_proposals", "type": e.__class__.__name__},
                conn_str=None,
            )
        except Exception:
            pass
        return []
