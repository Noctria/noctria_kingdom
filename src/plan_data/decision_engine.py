from __future__ import annotations
from typing import List, Dict, Any
from dataclasses import dataclass
import math, yaml, pathlib

from .contracts import FeatureBundle, StrategyProposal, OrderRequest
from .quality_gate import evaluate_quality

@dataclass
class DecisionEngineConfig:
    weights: Dict[str, float]
    rollout_percent: int
    min_confidence: float
    combine: str           # "best_one" or "weighted_sum"
    alpha_risk: float      # 0..1

    @staticmethod
    def from_yaml(path: str | pathlib.Path) -> "DecisionEngineConfig":
        with open(path, "r", encoding="utf-8") as f:
            y = yaml.safe_load(f)
        dflt = y.get("default", {})
        return DecisionEngineConfig(
            weights=y.get("weights", {}),
            rollout_percent=int(dflt.get("rollout_percent", 100)),
            min_confidence=float(dflt.get("min_confidence", 0.35)),
            combine=str(dflt.get("combine", "best_one")),
            alpha_risk=float(dflt.get("alpha_risk", 0.3)),
        )

class RoyalDecisionEngine:
    """
    提案①: NEW。複数AIの提案を集約して OrderRequest を1本にする。
    - DataQualityGateで品質を確認（FLAT/SCALE）
    - プロファイル重みでスコアリング
    - best_one: 最高スコアの提案を採択
    - weighted_sum: 方向一致の提案を合算（衝突はhighestへ倒す）
    """
    def __init__(self, cfg: DecisionEngineConfig):
        self.cfg = cfg

    def _score(self, p: StrategyProposal) -> float:
        w = self.cfg.weights.get(p.strategy, 0.0)
        # 信頼度と安全性（1 - risk_score）をブレンド
        return (1 - self.cfg.alpha_risk) * w * p.confidence + self.cfg.alpha_risk * (1 - p.risk_score)

    def _same_direction(self, intent_a: str, intent_b: str) -> bool:
        return intent_a == intent_b and intent_a in ("LONG", "SHORT")

    def decide(self, bundle: FeatureBundle, proposals: List[StrategyProposal]) -> OrderRequest:
        # 1) 品質ゲート
        qres = evaluate_quality(bundle)
        reasons = list(qres.reasons)

        # 2) 提案の正規化：min_confidence未満はFLAT扱い
        valid = []
        for p in proposals:
            if p.confidence < self.cfg.min_confidence or p.intent == "FLAT":
                continue
            valid.append(p)

        symbol = bundle.context.symbol

        # 3) フォールバック（品質NG or 候補なし）
        if qres.action == "FLAT" or not valid:
            return OrderRequest(symbol=symbol, intent="FLAT", qty=0.0, sources=proposals, trace_id=bundle.trace_id)

        # 4) qtyスケール（品質がSCALE判定のとき）
        qty_scale = qres.qty_scale if qres.action == "SCALE" else 1.0
        rollout_scale = max(0.01, self.cfg.rollout_percent / 100.0)

        # 5) スコアリング
        scored = sorted(((self._score(p), p) for p in valid), key=lambda t: t[0], reverse=True)

        # 6) 合成戦略
        if self.cfg.combine == "best_one":
            best_score, best = scored[0]
            qty = best.qty_raw * qty_scale * rollout_scale
            return OrderRequest(symbol=symbol, intent=best.intent, qty=qty,
                                order_type="MARKET", limit_price=best.price_hint,
                                sources=[best], trace_id=bundle.trace_id)
        else:  # "weighted_sum"
            # 方向が一致するものを合計。衝突したらスコア最大の方向に倒す
            by_dir: Dict[str, Dict[str, Any]] = {"LONG": {"qty": 0.0, "ps": []}, "SHORT": {"qty": 0.0, "ps": []}}
            for s, p in scored:
                if p.intent in ("LONG", "SHORT"):
                    by_dir[p.intent]["qty"] += p.qty_raw * (self.cfg.weights.get(p.strategy, 0.0)) * p.confidence
                    by_dir[p.intent]["ps"].append(p)
            long_qty, short_qty = by_dir["LONG"]["qty"], by_dir["SHORT"]["qty"]
            if long_qty == 0 and short_qty == 0:
                return OrderRequest(symbol=symbol, intent="FLAT", qty=0.0, sources=proposals, trace_id=bundle.trace_id)
            intent = "LONG" if long_qty >= short_qty else "SHORT"
            qty = (long_qty if intent == "LONG" else short_qty) * qty_scale * rollout_scale
            return OrderRequest(symbol=symbol, intent=intent, qty=qty, sources=by_dir[intent]["ps"], trace_id=bundle.trace_id)
