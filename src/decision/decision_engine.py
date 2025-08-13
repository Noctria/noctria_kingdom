# src/decision/decision_engine.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional

from src.plan_data.observability import log_decision

ENGINE_VERSION = "decision-min-0.1.1"


# -----------------------------
# Data models
# -----------------------------
@dataclass(frozen=True)
class DecisionRequest:
    """
    最小入力: 相関ID・シンボル・特徴量辞書
    features 例:
        {
          "volatility": 0.12,     # 0.0 以上
          "trend_score": 0.70     # 0.0..1.0 を想定
        }
    """
    trace_id: str
    symbol: str
    features: Dict[str, float]


@dataclass(frozen=True)
class DecisionResult:
    """
    最小出力: 採択した（想定）戦略名・スコア・理由・決定ペイロード
    decision 例:
        {
          "symbol": "USDJPY",
          "action": "enter_trend",
          "params": {"tp": 0.5, "sl": 0.3}
        }
    """
    strategy_name: str
    score: float
    reason: str
    decision: Dict[str, Any]


# -----------------------------
# Engine
# -----------------------------
class DecisionEngine:
    """
    最小版 Decision Engine（単純な閾値ルール）
      - 低ボラ + 強トレンド  : Prometheus_Oracle → enter_trend
      - 高ボラ + 弱トレンド  : Levia_Tempest     → scalp
      - それ以外（中庸）      : default_strategy   → range_trade

    観測:
      - obs_decisions に決定内容を1行保存（log_decision）
      - 既存のタイムラインビュー（obs_trace_timeline）で decision->>'action' を参照可能
    """

    def __init__(
        self,
        *,
        thr_vol_low: float = 0.15,
        thr_trend_strong: float = 0.60,
        default_strategy: str = "Aurus_Singularis",
        sl: float = 0.3,
        tp: float = 0.5,
    ) -> None:
        self.thr_vol_low = float(thr_vol_low)
        self.thr_trend_strong = float(thr_trend_strong)
        self.default_strategy = str(default_strategy)
        self._sl = float(sl)
        self._tp = float(tp)

    # -------- helpers --------
    @staticmethod
    def _get_feature(features: Dict[str, float], key: str, default: float) -> float:
        try:
            v = float(features.get(key, default))
        except (TypeError, ValueError):
            v = default
        return v

    @staticmethod
    def _clamp(x: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, x))

    # -------- main --------
    def decide(self, req: DecisionRequest, *, conn_str: Optional[str] = None) -> DecisionResult:
        # 特徴量の安全取得
        vol = max(0.0, self._get_feature(req.features, "volatility", 0.20))
        trend = self._clamp(self._get_feature(req.features, "trend_score", 0.0), 0.0, 1.0)

        # ルール判定
        if vol < self.thr_vol_low and trend >= self.thr_trend_strong:
            strategy = "Prometheus_Oracle"   # 低ボラ + 強トレンド
            action = "enter_trend"
            score = 0.90
            reason = f"trend={trend:.2f} strong & vol={vol:.2f} low"
        elif vol >= self.thr_vol_low and trend < self.thr_trend_strong:
            strategy = "Levia_Tempest"       # 高ボラ + 弱トレンド
            action = "scalp"
            score = 0.70
            reason = f"trend={trend:.2f} weak & vol={vol:.2f} high"
        else:
            strategy = self.default_strategy  # 中庸
            action = "range_trade"
            score = 0.60
            reason = f"trend={trend:.2f} mid & vol={vol:.2f} mid"

        decision_payload: Dict[str, Any] = {
            "symbol": req.symbol,
            "action": action,
            "params": {"tp": self._tp, "sl": self._sl},
        }

        # 観測ログ（決定）
        # features には入力生値をそのまま格納（将来の解析に役立つ）
        log_decision(
            trace_id=req.trace_id,
            engine_version=ENGINE_VERSION,
            strategy_name=strategy,
            score=score,
            reason=reason,
            features=req.features,
            decision=decision_payload,
            conn_str=conn_str,  # DSNが未指定なら環境変数 NOCTRIA_OBS_PG_DSN を使用
        )

        return DecisionResult(
            strategy_name=strategy,
            score=score,
            reason=reason,
            decision=decision_payload,
        )


__all__ = [
    "ENGINE_VERSION",
    "DecisionRequest",
    "DecisionResult",
    "DecisionEngine",
]
