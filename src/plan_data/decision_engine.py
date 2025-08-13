# src/plan_data/decision_engine.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import pathlib
import yaml

from .contracts import FeatureBundle, StrategyProposal, OrderRequest
from .quality_gate import evaluate_quality
from .observability import log_decision

ENGINE_VERSION = "royal-decision-0.2.0"

# =========================
# Config
# =========================
@dataclass
class DecisionEngineConfig:
    """
    - weights: 各戦略ごとの重み（0..+∞; 0は無効）
    - rollout_percent: ロールアウト比率（1..100）
    - min_confidence: 提案採択の最小信頼度（0..1）
    - combine:
        - "best_one": 最高スコアの提案を採択
        - "weighted_sum": 方向一致の提案を重み付き合算（衝突は大きい方に倒す）
    - alpha_risk: リスク寄与（0..1）。1に近いほど risk_score（高いほど危険）を強く減点
    """
    weights: Dict[str, float] = field(default_factory=dict)
    rollout_percent: int = 100
    min_confidence: float = 0.35
    combine: str = "best_one"          # "best_one" | "weighted_sum"
    alpha_risk: float = 0.30           # 0..1

    @staticmethod
    def from_yaml(path: str | pathlib.Path) -> "DecisionEngineConfig":
        with open(path, "r", encoding="utf-8") as f:
            y = yaml.safe_load(f) or {}
        dflt = y.get("default", {})
        return DecisionEngineConfig(
            weights=y.get("weights", {}) or {},
            rollout_percent=int(dflt.get("rollout_percent", 100)),
            min_confidence=float(dflt.get("min_confidence", 0.35)),
            combine=str(dflt.get("combine", "best_one")),
            alpha_risk=float(dflt.get("alpha_risk", 0.30)),
        )

    @classmethod
    def default(cls) -> "DecisionEngineConfig":
        return cls()

    def normalized(self) -> "DecisionEngineConfig":
        rp = max(1, min(int(self.rollout_percent), 100))
        mc = min(max(float(self.min_confidence), 0.0), 1.0)
        ar = min(max(float(self.alpha_risk), 0.0), 1.0)
        cmb = self.combine if self.combine in ("best_one", "weighted_sum") else "best_one"
        # 負の重みは0扱い
        weights = {k: (v if v > 0 else 0.0) for k, v in (self.weights or {}).items()}
        return DecisionEngineConfig(weights=weights, rollout_percent=rp, min_confidence=mc, combine=cmb, alpha_risk=ar)


# =========================
# Engine
# =========================
class RoyalDecisionEngine:
    """
    複数AIの StrategyProposal を統合し、最終的な OrderRequest を1本に決定する。
    手順:
      1) DataQualityGate（evaluate_quality）で品質評価（FLAT/OK/SCALE）
      2) min_confidence 未満は棄却、weights=0 は無効
      3) スコアリング: score = (1-alpha)*w*confidence + alpha*(1-risk_score)
      4) combine モード別に意思決定
      5) qty は 品質SCALE と rollout_percent を掛け合わせてスケーリング
      6) 観測ログ(obs_decisions)へ記録
    """

    def __init__(self, cfg: DecisionEngineConfig):
        self.cfg = cfg.normalized()

    # ---------- helpers ----------
    def _score(self, p: StrategyProposal) -> float:
        w = float(self.cfg.weights.get(p.strategy, 0.0))
        if w <= 0.0:
            return 0.0
        # confidence(0..1) を強調しつつ、risk_score(0..1; 高いほど危険) を減点
        # alpha_risk=0 で「重み*信頼度」単独、1 で「(1-risk)単独」
        return (1.0 - self.cfg.alpha_risk) * (w * float(p.confidence)) + self.cfg.alpha_risk * (1.0 - float(p.risk_score))

    @staticmethod
    def _is_dir(intent: str) -> bool:
        return intent in ("LONG", "SHORT")

    @staticmethod
    def _clamp_qty(x: float) -> float:
        # 下限0、過大値は任意に上限かけたい場合はここに clamp を追加
        return max(0.0, float(x))

    @staticmethod
    def _price_hint_aggregate(ps: List[StrategyProposal]) -> Optional[float]:
        # 有効な price_hint の平均（存在しない場合は None）
        vals = [float(p.price_hint) for p in ps if getattr(p, "price_hint", None) is not None]
        if not vals:
            return None
        return sum(vals) / len(vals)

    # ---------- main ----------
    def decide(self, bundle: FeatureBundle, proposals: List[StrategyProposal]) -> OrderRequest:
        symbol = bundle.context.symbol

        # 1) 品質ゲート
        qres = evaluate_quality(bundle)
        q_action: str = getattr(qres, "action", "OK")  # "OK" | "SCALE" | "FLAT"
        q_scale: float = float(getattr(qres, "qty_scale", 1.0) or 1.0)
        q_reasons: List[str] = list(getattr(qres, "reasons", []) or [])

        # 2) 正規化: min_conf未満/FLAT/重み0 は棄却
        valid: List[StrategyProposal] = []
        for p in proposals or []:
            if not self._is_dir(p.intent):
                continue
            if float(p.confidence) < self.cfg.min_confidence:
                continue
            if self.cfg.weights.get(p.strategy, 0.0) <= 0.0:
                continue
            valid.append(p)

        # 3) フォールバック（品質NG or 候補なし）
        if q_action == "FLAT" or not valid:
            # ログ（FLAT理由の可視化）
            reason = "quality=FLAT" if q_action == "FLAT" else "no_valid_proposals"
            try:
                log_decision(
                    trace_id=bundle.trace_id,
                    engine_version=ENGINE_VERSION,
                    strategy_name="RoyalDecisionEngine",
                    score=0.0,
                    reason=f"{reason}; reasons={q_reasons}",
                    features={
                        "symbol": symbol,
                        "timeframe": getattr(bundle.context, "timeframe", None),
                        "quality": {"action": q_action, "qty_scale": q_scale, "reasons": q_reasons},
                    },
                    decision={
                        "intent": "FLAT",
                        "qty": 0.0,
                        "combine": self.cfg.combine,
                        "rollout_percent": self.cfg.rollout_percent,
                        "min_confidence": self.cfg.min_confidence,
                    },
                )
            finally:
                return OrderRequest(symbol=symbol, intent="FLAT", qty=0.0, sources=proposals, trace_id=bundle.trace_id)

        # 4) qtyスケール
        rollout_scale = max(0.01, min(self.cfg.rollout_percent / 100.0, 1.0))
        qty_scale = q_scale if q_action == "SCALE" else 1.0
        total_scale = rollout_scale * qty_scale

        # 5) スコアリング
        scored: List[Tuple[float, StrategyProposal]] = sorted(
            ((self._score(p), p) for p in valid),
            key=lambda t: t[0],
            reverse=True,
        )

        # 6) 合成戦略
        if self.cfg.combine == "best_one":
            best_score, best = scored[0]
            qty = self._clamp_qty(best.qty_raw * total_scale)
            ord_req = OrderRequest(
                symbol=symbol,
                intent=best.intent,
                qty=qty,
                order_type="MARKET",
                limit_price=getattr(best, "price_hint", None),
                sources=[best],
                trace_id=bundle.trace_id,
            )

            # 観測ログ
            reason = "; ".join(
                [
                    f"combine=best_one",
                    f"chosen={best.strategy}:{best.intent}",
                    f"score={best_score:.3f}",
                    *(f"Q:{r}" for r in q_reasons),
                ]
            )
            log_decision(
                trace_id=bundle.trace_id,
                engine_version=ENGINE_VERSION,
                strategy_name="RoyalDecisionEngine",
                score=float(best_score),
                reason=reason,
                features={
                    "symbol": symbol,
                    "timeframe": getattr(bundle.context, "timeframe", None),
                    "quality": {"action": q_action, "qty_scale": q_scale, "reasons": q_reasons},
                    "top_candidates": [
                        {"strategy": p.strategy, "intent": p.intent, "score": s, "conf": p.confidence, "risk": p.risk_score}
                        for s, p in scored[:3]
                    ],
                },
                decision={
                    "intent": ord_req.intent,
                    "qty": ord_req.qty,
                    "order_type": getattr(ord_req, "order_type", "MARKET"),
                    "limit_price": getattr(ord_req, "limit_price", None),
                    "scale": {"rollout": rollout_scale, "quality": qty_scale},
                },
            )
            return ord_req

        # --- weighted_sum ---
        by_dir: Dict[str, Dict[str, Any]] = {"LONG": {"qty": 0.0, "ps": []}, "SHORT": {"qty": 0.0, "ps": []}}
        for s, p in scored:
            if not self._is_dir(p.intent):
                continue
            # 重み付き数量（重み * 信頼度 * 生数量）
            w = float(self.cfg.weights.get(p.strategy, 0.0))
            dir_qty = max(0.0, float(p.qty_raw)) * w * float(p.confidence)
            if dir_qty <= 0:
                continue
            by_dir[p.intent]["qty"] += dir_qty
            by_dir[p.intent]["ps"].append(p)

        long_qty = float(by_dir["LONG"]["qty"])
        short_qty = float(by_dir["SHORT"]["qty"])
        if long_qty == 0 and short_qty == 0:
            # 方向合成できなかった
            log_decision(
                trace_id=bundle.trace_id,
                engine_version=ENGINE_VERSION,
                strategy_name="RoyalDecisionEngine",
                score=0.0,
                reason=f"weighted_sum produced zero qty; reasons={q_reasons}",
                features={"symbol": symbol, "quality": {"action": q_action, "qty_scale": q_scale, "reasons": q_reasons}},
                decision={"intent": "FLAT", "qty": 0.0, "combine": "weighted_sum"},
            )
            return OrderRequest(symbol=symbol, intent="FLAT", qty=0.0, sources=proposals, trace_id=bundle.trace_id)

        intent = "LONG" if long_qty >= short_qty else "SHORT"
        base_qty = long_qty if intent == "LONG" else short_qty
        qty = self._clamp_qty(base_qty * total_scale)
        sources: List[StrategyProposal] = list(by_dir[intent]["ps"])
        price_hint = self._price_hint_aggregate(sources)

        ord_req = OrderRequest(
            symbol=symbol,
            intent=intent,
            qty=qty,
            order_type="MARKET",
            limit_price=price_hint,
            sources=sources,
            trace_id=bundle.trace_id,
        )

        # 観測ログ（weighted 合成）
        top_score, top_p = scored[0]
        reason = "; ".join(
            [
                "combine=weighted_sum",
                f"dir={intent}",
                f"qty_base={base_qty:.4f}",
                f"top={top_p.strategy}:{top_p.intent}@{top_score:.3f}",
                *(f"Q:{r}" for r in q_reasons),
            ]
        )
        log_decision(
            trace_id=bundle.trace_id,
            engine_version=ENGINE_VERSION,
            strategy_name="RoyalDecisionEngine",
            score=float(top_score),
            reason=reason,
            features={
                "symbol": symbol,
                "timeframe": getattr(bundle.context, "timeframe", None),
                "quality": {"action": q_action, "qty_scale": q_scale, "reasons": q_reasons},
                "dir_qty": {"LONG": long_qty, "SHORT": short_qty},
            },
            decision={
                "intent": ord_req.intent,
                "qty": ord_req.qty,
                "order_type": getattr(ord_req, "order_type", "MARKET"),
                "limit_price": getattr(ord_req, "limit_price", None),
                "scale": {"rollout": rollout_scale, "quality": qty_scale},
                "sources": [{"strategy": p.strategy, "conf": p.confidence, "risk": p.risk_score} for p in sources[:5]],
            },
        )
        return ord_req


__all__ = [
    "DecisionEngineConfig",
    "RoyalDecisionEngine",
    "ENGINE_VERSION",
]
