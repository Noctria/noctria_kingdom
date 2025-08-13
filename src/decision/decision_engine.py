from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any

from src.plan_data.observability import log_decision

ENGINE_VERSION = "decision-min-0.1.0"

@dataclass
class DecisionRequest:
    trace_id: str
    symbol: str
    features: Dict[str, float]  # 例: {"volatility": 0.12, "trend_score": 0.7}

@dataclass
class DecisionResult:
    strategy_name: str
    score: float
    reason: str
    decision: Dict[str, Any]  # 例: {"action": "enter_long", "tp": 0.5, "sl": 0.3}

class DecisionEngine:
    """
    最小版 Decision Engine（閾値ルールのみ）
    """

    def __init__(
        self,
        thr_vol_low: float = 0.15,
        thr_trend_strong: float = 0.6,
        default_strategy: str = "Aurus_Singularis",
    ):
        self.thr_vol_low = thr_vol_low
        self.thr_trend_strong = thr_trend_strong
        self.default_strategy = default_strategy

    def decide(self, req: DecisionRequest) -> DecisionResult:
        vol = float(req.features.get("volatility", 0.2))
        trend = float(req.features.get("trend_score", 0.0))

        if vol < self.thr_vol_low and trend >= self.thr_trend_strong:
            strategy = "Prometheus_Oracle"   # 低ボラ + 強トレンド
            action = "enter_trend"
            score = 0.9
            reason = f"trend={trend:.2f} strong & vol={vol:.2f} low"
        elif vol >= self.thr_vol_low and trend < self.thr_trend_strong:
            strategy = "Levia_Tempest"       # 高ボラ + 弱トレンド
            action = "scalp"
            score = 0.7
            reason = f"trend={trend:.2f} weak & vol={vol:.2f} high"
        else:
            strategy = self.default_strategy  # 中庸
            action = "range_trade"
            score = 0.6
            reason = f"trend={trend:.2f} mid & vol={vol:.2f} mid"

        decision_payload = {
            "symbol": req.symbol,
            "action": action,
            "params": {"tp": 0.5, "sl": 0.3},  # ダミー
        }

        # 観測ログ（決定）
        log_decision(
            trace_id=req.trace_id,
            engine_version=ENGINE_VERSION,
            strategy_name=strategy,
            score=score,
            reason=reason,
            features=req.features,
            decision=decision_payload,
        )

        return DecisionResult(
            strategy_name=strategy,
            score=score,
            reason=reason,
            decision=decision_payload,
        )
