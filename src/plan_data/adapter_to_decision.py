#!/usr/bin/env python3
# coding: utf-8
"""
Adapter/facade from Plan layer to DecisionEngine.

- strategies から proposals を作り、DecisionEngine.decide(...) へ委譲
- 余分な引数が来ても壊れないように寛容に受ける
- plan_data.contracts が無くても最小フォールバックで動く
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

# 依存（存在すれば正式型、無ければフォールバック）
try:
    from plan_data.contracts import FeatureBundle, StrategyProposal  # type: ignore
except Exception:

    class FeatureBundle:  # 最小フォールバック
        def __init__(self, df=None, context=None):
            self.df = df
            self.context = context

    class StrategyProposal(dict):  # dict 互換で十分
        pass


# DecisionEngine は top-level パッケージ `decision` 配下にある想定（tests/conftest が sys.path を整備）
from decision.decision_engine import DecisionEngine, DecisionRecord  # type: ignore


def _materialize_proposals(
    strategies: Any,
    bundle: FeatureBundle,
) -> List[StrategyProposal]:
    """
    strategies から StrategyProposal の配列を作る。
    - strategy に propose(bundle)->dict/obj があれば呼ぶ
    - すでに dict/StrategyProposal の配列ならそのまま返す
    - 単一 strategy も配列に包む
    """
    # 既に proposals っぽい
    if isinstance(strategies, list) and (
        not strategies or isinstance(strategies[0], (dict, StrategyProposal))
    ):
        return [
            StrategyProposal(p) if not isinstance(p, StrategyProposal) else p for p in strategies
        ]

    # 単一 → 配列
    seq: Iterable[Any]
    if isinstance(strategies, (tuple, list)):
        seq = strategies
    else:
        seq = [strategies]

    out: List[StrategyProposal] = []
    for s in seq:
        if s is None:
            continue
        # .propose(bundle) があれば呼ぶ
        prop = None
        if hasattr(s, "propose"):
            try:
                prop = s.propose(bundle)  # type: ignore[attr-defined]
            except Exception:
                prop = None
        # 無ければ、よくある属性から拾って dict 化
        if prop is None:
            d: Dict[str, Any] = {}
            for k in (
                "name",
                "strategy",
                "symbol",
                "side",
                "action",
                "lot",
                "size",
                "price",
                "tp",
                "sl",
                "ttl",
                "risk_score",
                "score",
                "extra",
            ):
                v = getattr(s, k, None)
                if v is not None:
                    d[k] = v
            if d:
                prop = d
        if prop is not None:
            out.append(StrategyProposal(prop) if not isinstance(prop, StrategyProposal) else prop)
    return out


def run_strategy_and_decide(
    bundle: FeatureBundle,
    strategies: Any,
    *,
    quality: Any | None = None,
    profiles: Dict[str, Any] | None = None,
    conn_str: str | None = None,
    **kwargs: Any,
) -> Tuple[DecisionRecord, Dict[str, Any]]:
    """
    Plan 層から呼ばれる統合ファサード。
    - strategies から proposals を作成
    - DecisionEngine.decide(...) へ委譲
    余分な引数（kwargs）は無視するのでテスト側の差異に強いです。
    """
    engine = DecisionEngine()
    proposals = _materialize_proposals(strategies, bundle)
    record, decision = engine.decide(
        bundle,
        proposals,
        quality=quality,
        profiles=profiles,
        conn_str=conn_str,
    )
    return record, decision


__all__ = ["run_strategy_and_decide", "FeatureBundle", "StrategyProposal"]
