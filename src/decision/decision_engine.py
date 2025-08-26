# src/decision/decision_engine.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional

ENGINE_VERSION = "decision-min-0.2.0"  # bump: quality hints support

# 観測ログ: 実行環境の import 事情に左右されないようフォールバック付き
try:
    from plan_data.observability import log_decision  # type: ignore
except Exception:
    from src.plan_data.observability import log_decision  # type: ignore


# -----------------------------
# Data models
# -----------------------------
@dataclass(frozen=True)
class DecisionRequest:
    """
    最小入力: 相関ID・シンボル・特徴量辞書
    features 例:
        {
          "volatility": 0.12,         # 0.0 以上
          "trend_score": 0.70,        # 0.0..1.0 を想定

          # --- 任意（あれば品質に基づくサイズ調整を適用）---
          "base_qty": 100.0,          # 提案元の推奨サイズ（任意）
          "quality_action": "SCALE",  # "OK"|"SCALE"|"FLAT"（任意）
          "qty_scale": 0.5            # SCALE時のスケール係数（任意）
        }
    """
    trace_id: str
    symbol: str
    features: Dict[str, float | int | str]


@dataclass(frozen=True)
class DecisionResult:
    """
    最小出力: 採択した（想定）戦略名・スコア・理由・決定ペイロード
    decision 例:
        {
          "symbol": "USDJPY",
          "action": "enter_trend",
          "params": {"tp": 0.5, "sl": 0.3},
          "size": 50.0,                              # <- 任意（base_qty があれば出力）
          "quality": {"action": "SCALE", "scale": 0.5}
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

    拡張:
      - features に `base_qty` / `quality_action` / `qty_scale` が含まれていれば、
        FLAT/SCALE を反映して `decision["size"]` と `decision["quality"]` を出力・保存。
      - 指定が無ければ従来どおり（サイズ未設定）。
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
    def _get_float(d: Dict[str, Any], key: str, default: float) -> float:
        try:
            v = float(d.get(key, default))
        except (TypeError, ValueError):
            v = default
        return v

    @staticmethod
    def _get_str(d: Dict[str, Any], key: str, default: str) -> str:
        v = d.get(key, default)
        return str(v) if v is not None else default

    @staticmethod
    def _clamp(x: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, x))

    # -------- main --------
    def decide(self, req: DecisionRequest, *, conn_str: Optional[str] = None) -> DecisionResult:
        f = req.features

        # 特徴量の安全取得
        vol = max(0.0, self._get_float(f, "volatility", 0.20))
        trend = self._clamp(self._get_float(f, "trend_score", 0.0), 0.0, 1.0)

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

        # ---- optional: quality-based sizing ----
        # adapter 側で proposal.meta に付与された "quality_action"/"qty_scale" を
        # 上位から features で受け取る設計（互換性のため任意）。
        base_qty = f.get("base_qty", None)
        if base_qty is not None:
            try:
                base_qty = float(base_qty)
            except (TypeError, ValueError):
                base_qty = None

        quality_action = self._get_str(f, "quality_action", "").upper() if isinstance(f, dict) else ""
        qty_scale = self._get_float(f, "qty_scale", 1.0)

        final_qty: Optional[float] = None
        quality_out: Optional[Dict[str, Any]] = None

        if base_qty is not None:
            if quality_action == "FLAT":
                final_qty = 0.0
                quality_out = {"action": "FLAT", "scale": 0.0}
                reason += " | quality=FLAT"
            elif quality_action == "SCALE":
                final_qty = max(0.0, base_qty * max(0.0, qty_scale))
                quality_out = {"action": "SCALE", "scale": float(qty_scale)}
                reason += f" | quality=SCALE({qty_scale:.2f})"
            else:
                final_qty = max(0.0, base_qty)
                if quality_action:
                    # 何かしら文字列が来ていたらメモだけ残す
                    quality_out = {"action": quality_action, "scale": float(qty_scale)}
                else:
                    quality_out = {"action": "OK", "scale": 1.0}

            decision_payload["size"] = final_qty
            decision_payload["quality"] = quality_out

        # 観測ログ（決定）: 失敗は握りつぶして本処理を継続（他モジュールと整合）
        try:
            log_decision(
                trace_id=req.trace_id,
                engine_version=ENGINE_VERSION,
                strategy_name=strategy,
                score=score,
                reason=reason,
                features=req.features,   # 入力の生値を保存（quality hintsも含む）
                decision=decision_payload,
                conn_str=conn_str,       # DSN未指定なら env NOCTRIA_OBS_PG_DSN
            )
        except Exception:
            pass

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
