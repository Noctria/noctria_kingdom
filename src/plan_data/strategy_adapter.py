# src/plan_data/strategy_adapter.py
from __future__ import annotations

import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Protocol, runtime_checkable

import pandas as pd

from plan_data.observability import log_infer_call
from plan_data.trace import get_trace_id, new_trace_id

# --- Contracts (超軽量版) ---

@dataclass
class FeatureBundle:
    """
    共通入力コンテナ（最小版）
    - df: 特徴量テーブル
    - context: メタ情報（symbol, timeframe など）
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
    """
    戦略の共通出力（最小版）
    """
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
      - timeout_sec は簡易実装（実スレッド停止はしない）：計測超過時は log の success=False を付与
    """
    model = model_name or getattr(strategy, "__class__", type("X",(object,),{})).__name__
    ver = model_version or getattr(strategy, "VERSION", "dev")

    # trace_id を決定（優先度: 引数 > コンテキスト > 自動生成）
    trace_id = trace_id or get_trace_id() or new_trace_id(
        symbol=str(features.context.get("symbol", "MULTI")),
        timeframe=str(features.context.get("timeframe", "1d")),
    )

    t0 = time.time()
    success = False
    proposal: Optional[StrategyProposal] = None
    err: Optional[Exception] = None

    try:
        if isinstance(strategy, _ProposeLike):
            proposal = strategy.propose(features, **kwargs)
        elif isinstance(strategy, _PredictLike):
            proposal = strategy.predict_future(features, **kwargs)
        else:
            # 動的ディスパッチ（シグネチャが少し違っても拾う）
            if hasattr(strategy, "propose"):
                proposal = getattr(strategy, "propose")(features, **kwargs)
            elif hasattr(strategy, "predict_future"):
                proposal = getattr(strategy, "predict_future")(features, **kwargs)
            else:
                raise AttributeError(f"{model} has neither propose() nor predict_future().")
        success = True
        return proposal  # type: ignore[return-value]
    except Exception as e:
        err = e
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
