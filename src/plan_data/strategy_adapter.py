# src/plan_data/strategy_adapter.py
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, runtime_checkable, Iterable, Tuple

import pandas as pd

# 観測は失敗しても握りつぶす方針（オフラインでも動く）
try:
    from plan_data.observability import log_infer_call  # type: ignore
except Exception:
    from src.plan_data.observability import log_infer_call  # type: ignore

try:
    from plan_data.trace import get_trace_id, new_trace_id  # type: ignore
except Exception:
    from src.plan_data.trace import get_trace_id, new_trace_id  # type: ignore


# --- Contracts (超軽量版) ---

@dataclass
class FeatureBundle:
    """
    共通入力コンテナ（最小版）
    - df: 特徴量テーブル（最新行が提案入力の主対象）
    - context: メタ情報（symbol, timeframe, data_lag_min, missing_ratioなど）
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
    def propose(self, features: Any, **kwargs) -> StrategyProposal: ...


@runtime_checkable
class _PredictLike(Protocol):
    def predict_future(self, features: Any, **kwargs) -> StrategyProposal: ...


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

    return StrategyProposal(
        symbol=str(p.symbol or p.meta.get("symbol") or "UNKNOWN"),
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


def _bundle_to_dict_and_order(features: FeatureBundle) -> Tuple[Dict[str, Any], Optional[list[str]]]:
    """
    Aurus など「dict で .get する」戦略向けに FeatureBundle を辞書へ変換。
    - ベース: 最新行（tail）を dict 化
    - 併せて context も 'ctx_*' で補助的に混ぜる（キー衝突は tail が優先）
    - feature_order はそのまま返す（必要なら戦略へ渡す）
    """
    base: Dict[str, Any] = {}
    try:
        tail = features.tail_row()
        if isinstance(tail, pd.Series):
            base.update({str(k): tail[k] for k in tail.index})
    except Exception:
        pass

    ctx = dict(features.context or {})
    for k, v in ctx.items():
        key = f"ctx_{k}" if k not in base else k  # 衝突時は列名優先
        if key not in base:
            base[key] = v

    return base, (features.feature_order or None)


def _maybe_retry_with_dict(strategy: Any, call_name: str, features: FeatureBundle, **kwargs) -> Any:
    """
    propose()/predict_future() を FeatureBundle で呼び、典型的な AttributeError(.get) などの場合は
    dict へ変換して **再試行** する互換レイヤ。
    """
    fn = getattr(strategy, call_name)

    # 1回目: そのまま FeatureBundle を渡して試す
    try:
        return fn(features, **kwargs)
    except AttributeError as e:
        msg = str(e)
        # 代表的な互換パターン: 'FeatureBundle' object has no attribute 'get'
        if "has no attribute 'get'" in msg or ".get" in msg:
            feat_dict, order = _bundle_to_dict_and_order(features)
            # feature_order を kwargs に補助的に入れる（必要な戦略がある）
            if order is not None and "feature_order" not in kwargs:
                kwargs = {**kwargs, "feature_order": order}
            return fn(feat_dict, **kwargs)
        raise
    except TypeError as e:
        # 引数ミスマッチ時も辞書で再試行してみる
        feat_dict, order = _bundle_to_dict_and_order(features)
        if order is not None and "feature_order" not in kwargs:
            kwargs = {**kwargs, "feature_order": order}
        return fn(feat_dict, **kwargs)


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
      - 引数が FeatureBundle 非対応の戦略には dict へ自動変換して再試行（Aurus 系対策）
      - 例外は上位に送出するが、観測ログは成功/失敗ともに記録
      - timeout_sec は簡易実装（実スレッド停止はしない）：計測超過時は success=False を log
      - 戻り値が dict/NamedTuple でも StrategyProposal に変換
    """
    model = model_name or getattr(getattr(strategy, "__class__", None), "__name__", str(type(strategy).__name__))
    ver = model_version or getattr(strategy, "VERSION", "dev")

    # trace_id を決定（優先度: 引数 > コンテキスト > 自動生成）
    trace_id = trace_id or get_trace_id() or new_trace_id(
        symbol=str(features.context.get("symbol", "MULTI")),
        timeframe=str(features.context.get("timeframe", "1d")),
    )

    t0 = time.time()
    success = False
    proposal: Optional[StrategyProposal] = None

    try:
        # 構造的チェック or ダックタイピングで呼び分け、辞書再試行付き
        if isinstance(strategy, _ProposeLike) or hasattr(strategy, "propose"):
            raw = _maybe_retry_with_dict(strategy, "propose", features, **kwargs)
        elif isinstance(strategy, _PredictLike) or hasattr(strategy, "predict_future"):
            raw = _maybe_retry_with_dict(strategy, "predict_future", features, **kwargs)
        else:
            raise AttributeError(f"{model} has neither propose() nor predict_future().")

        proposal = _coerce_to_proposal(raw, default_symbol=str(features.context.get("symbol", "MULTI")))
        success = True
        return proposal
    except Exception:
        # 例外は上位に再送出（finally で log は必ず記録）
        raise
    finally:
        dur_ms = int((time.time() - t0) * 1000)
        # timeout 判定（簡易）
        if timeout_sec is not None and (dur_ms / 1000.0) > timeout_sec:
            success = False

        try:
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
