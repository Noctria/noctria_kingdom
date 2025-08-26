# src/plan_data/strategy_adapter.py
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, runtime_checkable, Iterable, List

import pandas as pd

from plan_data.observability import log_infer_call
from plan_data.trace import get_trace_id, new_trace_id
from plan_data.quality_gate import evaluate_quality, QualityResult


# --- Contracts (超軽量版) ---

@dataclass
class FeatureBundle:
    """
    共通入力コンテナ（最小版）
    - df: 特徴量テーブル
    - context: メタ情報（symbol, timeframe, data_lag_min, missing_ratio など）
    - feature_order: 並び順ヒント（必要な戦略向け）
    """
    df: pd.DataFrame
    context: Dict[str, Any]
    feature_order: Optional[list[str]] = None
    version: str = "1.0.0"  # 将来の互換管理用

    def tail_row(self) -> pd.Series:
        return self.df.iloc[-1] if len(self.df) else pd.Series(dtype="float64")


@dataclass
class StrategyProposal:
    """戦略の共通出力（最小版）"""
    symbol: str
    direction: str        # "LONG" / "SHORT" / "FLAT"
    qty: float
    confidence: float     # 0.0 ~ 1.0
    reasons: list[str]
    meta: Dict[str, Any]
    schema_version: str = "1.0.0"


# --- Strategy 呼出契約（プロトコル） ---

@runtime_checkable
class _ProposeLike(Protocol):
    def propose(self, features: FeatureBundle, **kwargs) -> StrategyProposal: ...


@runtime_checkable
class _PredictLike(Protocol):
    def predict_future(self, features: FeatureBundle, **kwargs) -> StrategyProposal: ...


# --- 内部ユーティリティ ---

_VALID_DIRECTIONS = {"LONG", "SHORT", "FLAT"}


def _to_list_str(x: Any) -> list[str]:
    if x is None:
        return []
    if isinstance(x, str):
        return [x]
    if isinstance(x, Iterable):
        return [str(v) for v in x]
    return [str(x)]


def _normalize_proposal(p: StrategyProposal) -> StrategyProposal:
    # direction 正規化
    direction = (p.direction or "FLAT").upper()
    if direction not in _VALID_DIRECTIONS:
        direction = "FLAT"

    # qty, confidence 正規化
    try:
        qty = float(p.qty)
    except Exception:
        qty = 0.0
    try:
        conf = float(p.confidence)
    except Exception:
        conf = 0.0
    conf = max(0.0, min(1.0, conf))

    reasons = _to_list_str(p.reasons)

    # symbol
    sym = str(p.symbol or p.meta.get("symbol") or "UNKNOWN")

    return StrategyProposal(
        symbol=sym,
        direction=direction,
        qty=qty,
        confidence=conf,
        reasons=reasons,
        meta=dict(p.meta or {}),
        schema_version=str(p.schema_version or "1.0.0"),
    )


def _coerce_to_proposal(obj: Any, default_symbol: str) -> StrategyProposal:
    """dict/NamedTuple/他クラスから StrategyProposal へ極力寄せる"""
    if isinstance(obj, StrategyProposal):
        return _normalize_proposal(obj)

    if isinstance(obj, dict):
        cand = StrategyProposal(
            symbol=str(obj.get("symbol") or default_symbol or "UNKNOWN"),
            direction=str(obj.get("direction") or "FLAT"),
            qty=float(obj.get("qty") or 0.0),
            confidence=float(obj.get("confidence") or 0.0),
            reasons=_to_list_str(obj.get("reasons")),
            meta=dict(obj.get("meta") or {}),
            schema_version=str(obj.get("schema_version") or "1.0.0"),
        )
        return _normalize_proposal(cand)

    # NamedTuple や属性持ちオブジェクト
    try:
        cand = StrategyProposal(
            symbol=str(getattr(obj, "symbol", default_symbol) or default_symbol or "UNKNOWN"),
            direction=str(getattr(obj, "direction", "FLAT")),
            qty=float(getattr(obj, "qty", 0.0)),
            confidence=float(getattr(obj, "confidence", 0.0)),
            reasons=_to_list_str(getattr(obj, "reasons", [])),
            meta=dict(getattr(obj, "meta", {}) or {}),
            schema_version=str(getattr(obj, "schema_version", "1.0.0")),
        )
        return _normalize_proposal(cand)
    except Exception:
        # 最終フォールバック（何も読めない時）
        return StrategyProposal(
            symbol=str(default_symbol or "UNKNOWN"),
            direction="FLAT",
            qty=0.0,
            confidence=0.0,
            reasons=["invalid proposal object"],
            meta={"raw": repr(obj)},
            schema_version="1.0.0",
        )


def _apply_quality(q: QualityResult, p: StrategyProposal) -> StrategyProposal:
    """
    Quality Gate 出力に基づいて提案を補正:
      - FLAT: direction=FLAT, qty=0
      - SCALE: qty *= qty_scale
      - OK: そのまま
    また meta に quality_* と context 重要値を埋め込む。
    """
    meta = dict(p.meta or {})
    meta.update(
        {
            "quality_action": q.action,
            "qty_scale": float(q.qty_scale),
            "quality_reasons": list(q.reasons or []),
        }
    )

    # 方向/数量の補正
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
    elif q.action == "SCALE":
        scaled_qty = max(0.0, float(p.qty) * float(q.qty_scale))
        return StrategyProposal(
            symbol=p.symbol,
            direction=p.direction,
            qty=scaled_qty,
            confidence=float(p.confidence),
            reasons=[*list(p.reasons or []), f"quality:SCALE x{q.qty_scale:.2f}"],
            meta=meta,
            schema_version=p.schema_version,
        )
    else:
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


def _inject_context_meta(p: StrategyProposal, ctx: Dict[str, Any]) -> StrategyProposal:
    """
    監視・GUI用に context の重要値を meta に併記（欠けていても続行）。
    """
    meta = dict(p.meta or {})
    for k in ("symbol", "timeframe", "data_lag_min", "missing_ratio", "trace_id"):
        if k in ctx and k not in meta:
            meta[k] = ctx[k]
    return StrategyProposal(
        symbol=p.symbol,
        direction=p.direction,
        qty=p.qty,
        confidence=p.confidence,
        reasons=list(p.reasons or []),
        meta=meta,
        schema_version=p.schema_version,
    )


# --- Adapter ---

def propose_with_logging(
    strategy: Any,
    features: FeatureBundle,
    *,
    model_name: Optional[str] = None,
    model_version: Optional[str] = None,
    timeout_sec: Optional[float] = None,
    trace_id: Optional[str] = None,
    conn_str: Optional[str] = None,  # None なら env NOCTRIA_OBS_PG_DSN
    **kwargs,
) -> StrategyProposal:
    """
    どの戦略でも共通に呼べるラッパ:
      - .propose(...) があればそれを使用、無ければ .predict_future(...) を探す
      - 例外は上位に送出するが、観測ログは成功/失敗ともに記録
      - timeout_sec は簡易実装（実スレッド停止はしない）：計測超過時は success=False を log
      - 戻り値が dict/NamedTuple でも StrategyProposal に変換
      - **Quality Gate を自動適用**し、数量/方向/メタに反映
    """
    model = model_name or getattr(getattr(strategy, "__class__", None), "__name__", str(type(strategy).__name__))
    ver = model_version or getattr(strategy, "VERSION", "dev")

    # trace_id を決定（優先度: 引数 > コンテキスト > 自動生成）
    trace_id = trace_id or features.context.get("trace_id") or get_trace_id() or new_trace_id(
        symbol=str(features.context.get("symbol", "MULTI")),
        timeframe=str(features.context.get("timeframe", "1d")),
    )

    t0 = time.time()
    success = False
    final_proposal: Optional[StrategyProposal] = None

    try:
        # まず Protocol での構造的チェック
        if isinstance(strategy, _ProposeLike):
            raw = strategy.propose(features, **kwargs)
        elif isinstance(strategy, _PredictLike):
            raw = strategy.predict_future(features, **kwargs)
        else:
            # 動的ディスパッチ（duck typing）
            if hasattr(strategy, "propose"):
                raw = getattr(strategy, "propose")(features, **kwargs)
            elif hasattr(strategy, "predict_future"):
                raw = getattr(strategy, "predict_future")(features, **kwargs)
            else:
                raise AttributeError(f"{model} has neither propose() nor predict_future().")

        # 正規化
        proposal0 = _coerce_to_proposal(raw, default_symbol=str(features.context.get("symbol", "MULTI")))

        # Quality Gate 評価 & 適用
        qres: QualityResult = evaluate_quality(features)
        proposal1 = _apply_quality(qres, proposal0)

        # context の重要値を meta に合流（GUI/監視用）
        proposal2 = _inject_context_meta(proposal1, features.context or {})

        final_proposal = proposal2
        success = True
        return final_proposal

    except Exception:
        # 例外は上位に再送出（finally で log は必ず記録）
        raise

    finally:
        dur_ms = int((time.time() - t0) * 1000)
        # timeout 判定（簡易）
        if timeout_sec is not None and (dur_ms / 1000.0) > timeout_sec:
            success = False

        try:
            # 旧々フォーム互換で記録（GUI でも見える dur_ms/ts を確保）
            log_infer_call(
                conn_str or None,
                model=model,
                ver=str(ver),
                dur_ms=dur_ms,
                success=bool(success),
                feature_staleness_min=int(features.context.get("feature_staleness_min", 0) or 0),
                trace_id=trace_id,
            )
        except Exception:
            # 観測ログ失敗は握りつぶし
            pass


__all__ = [
    "FeatureBundle",
    "StrategyProposal",
    "propose_with_logging",
]
