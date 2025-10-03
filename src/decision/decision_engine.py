# src/decision/decision_engine.py
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Tuple

# --- DecisionRecord: 既存の場所を優先して import、無ければフォールバック ----
try:
    from decision.decision_record import DecisionRecord  # 既存プロジェクト互換
except Exception:  # 最低限の互換レコード

    @dataclass
    class DecisionRecord:
        trace_id: str
        engine_version: str
        strategy_name: str
        score: float
        reason: str
        features: Dict[str, Any]
        decision: Dict[str, Any]


# Plan 側コンポーネント（実行時循環を避けたいので TYPE_CHECKING 時のみ型参照）
if TYPE_CHECKING:
    from plan_data.contracts import FeatureBundle, StrategyProposal  # type: ignore
else:
    FeatureBundle = Any  # 走行時はゆるく扱う
    StrategyProposal = Any

# 観測ログ（あれば使う／無ければ握りつぶす）
try:
    from plan_data import observability  # type: ignore
except Exception:  # ダミー

    class _ObsDummy:
        def log_decision(self, *a, **k):  # noqa: N802
            pass

    observability = _ObsDummy()  # type: ignore


DictLike = Dict[str, Any]
log = logging.getLogger("noctria.decision_engine")


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """obj が dict でもオブジェクトでも安全に属性を読むヘルパ。"""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


# ----------------------------------------------------------------------
# 互換シム: 一部コードが DecisionRequest.context を参照するため後方互換対応
# ----------------------------------------------------------------------
@dataclass
class DecisionRequest:
    trace_id: str
    symbol: str
    features: Dict[str, Any]
    context: Any = field(default=None)

    def __post_init__(self):
        if self.context is None:

            class _Ctx:
                def __init__(self, trace_id: str, symbol: str):
                    self.trace_id = trace_id
                    self.symbol = symbol

            self.context = _Ctx(self.trace_id, self.symbol)


@dataclass
class DecisionResult:
    strategy_name: str
    score: float
    reason: str
    decision: Dict[str, Any]


class DecisionEngine:
    """
    最終意思決定エンジン（軽量実装）
    - 入力: FeatureBundle + 各AIの StrategyProposal 群
    - NoctusGate で実行前リスクチェック（存在すれば）
    - 観測ログ（存在すれば）へ記録
    """

    def __init__(self, version: str = "DecisionEngine/1.0"):
        self.version = version
        self._records: List[DecisionRecord] = []

    # 既存の簡易 API 互換
    def add_record(self, record: DecisionRecord):
        self._records.append(record)

    def get_records(self) -> List[DecisionRecord]:
        return list(self._records)

    # ---- 主要API ------------------------------------------------------------
    def decide(
        self,
        bundle: FeatureBundle,
        proposals: Iterable[StrategyProposal],
        *,
        quality: Any | None = None,
        profiles: DictLike | None = None,
        conn_str: Optional[str] = None,
    ) -> Tuple[DecisionRecord, DictLike]:
        """
        proposals から 1件選択し、NoctusGate チェックを適用して最終決定を返す。
        戻り値: (DecisionRecord, decision_dict)
        """
        trace_id = _get(getattr(bundle, "context", None), "trace_id", None) or _get(
            bundle, "trace_id", "N/A"
        )

        # 候補整形
        proposals_list: List[StrategyProposal] = list(proposals or [])
        if not proposals_list:
            decision = {
                "action": "HOLD",
                "reason": "no proposals",
                "size": 0.0,
                "symbol": _get(
                    getattr(bundle, "context", None),
                    "symbol",
                    _get(bundle, "symbol", "USDJPY"),
                ),
            }
            rec = self._log_and_build_record(
                trace_id=trace_id,
                bundle=bundle,
                decision=decision,
                reason=decision["reason"],
                strategy_name="(none)",
                score=0.0,
                conn_str=conn_str,
            )
            self.add_record(rec)
            return rec, decision

        # スコア最大（無ければ先頭）
        best = self._pick_best(proposals_list)

        # NoctusGate（あればチェック）
        try:
            from plan_data import noctus_gate as noctus_gate_mod  # type: ignore

            ng_res = noctus_gate_mod.check_proposal(best, conn_str=conn_str)
        except Exception:
            ng_res = type("NG", (), {"ok": True, "reasons": []})()  # 常に通過

        if not getattr(ng_res, "ok", True):
            decision = {
                "action": "REJECT",
                "reason": "NoctusGate blocked: " + "; ".join(_get(ng_res, "reasons", []) or []),
                "size": float(_get(best, "lot", _get(best, "size", 0.0)) or 0.0),
                "symbol": _get(
                    best,
                    "symbol",
                    _get(getattr(bundle, "context", None), "symbol", "USDJPY"),
                ),
                "proposal": self._proposal_to_dict(best),
            }
            rec = self._log_and_build_record(
                trace_id=trace_id,
                bundle=bundle,
                decision=decision,
                reason=decision["reason"],
                strategy_name=str(_get(best, "name", _get(best, "strategy", "unknown"))),
                score=float(_get(best, "score", 0.0) or 0.0),
                conn_str=conn_str,
            )
            self.add_record(rec)
            return rec, decision

        # 実行アクション
        action = str(_get(best, "action", _get(best, "side", "HOLD")) or "HOLD").upper()
        size = float(_get(best, "lot", _get(best, "size", 0.0)) or 0.0)
        symbol = _get(best, "symbol", _get(getattr(bundle, "context", None), "symbol", "USDJPY"))

        reason_list: List[str] = []
        if quality is not None and not _get(quality, "ok", True):
            reasons = _get(quality, "reasons", []) or []
            reasons_s = ", ".join(str(r) for r in reasons)
            reason_list.append(f"quality={_get(quality, 'action', 'NG')}({reasons_s})")

        decision: Dict[str, Any] = {
            "action": action,
            "symbol": symbol,
            "size": size,
            "proposal": self._proposal_to_dict(best),
        }
        if reason_list:
            decision["reason"] = "; ".join(reason_list)

        rec = self._log_and_build_record(
            trace_id=trace_id,
            bundle=bundle,
            decision=decision,
            reason=decision.get("reason", ""),
            strategy_name=str(_get(best, "name", _get(best, "strategy", "unknown"))),
            score=float(_get(best, "score", 0.0) or 0.0),
            conn_str=conn_str,
        )
        self.add_record(rec)
        return rec, decision

    # ---- 内部ユーティリティ -------------------------------------------------
    def _pick_best(self, proposals: List[StrategyProposal]) -> StrategyProposal:
        scored = [(float(_get(p, "score", 0.0) or 0.0), idx, p) for idx, p in enumerate(proposals)]
        scored.sort(key=lambda t: t[0], reverse=True)
        return scored[0][2] if scored else proposals[0]

    def _proposal_to_dict(self, p: StrategyProposal) -> DictLike:
        if isinstance(p, dict):
            return dict(p)
        keys = (
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
        )
        out: Dict[str, Any] = {}
        for k in keys:
            v = getattr(p, k, None)
            if v is not None:
                out[k] = v
        return out

    def _log_and_build_record(
        self,
        *,
        trace_id: str,
        bundle: FeatureBundle,
        decision: DictLike,
        reason: str,
        strategy_name: str,
        score: float,
        conn_str: Optional[str],
    ) -> DecisionRecord:
        features_dict = self._features_to_dict(bundle)
        try:
            observability.log_decision(  # type: ignore[attr-defined]
                trace_id=trace_id,
                engine_version=self.version,
                strategy_name=strategy_name,
                score=float(score),
                reason=reason,
                features=features_dict,
                decision=decision,
                conn_str=conn_str,
            )
        except Exception as e:
            log.warning("log_decision failed: %s (trace_id=%s)", e, trace_id)
        return DecisionRecord(
            trace_id=trace_id,
            engine_version=self.version,
            strategy_name=strategy_name,
            score=float(score),
            reason=reason,
            features=features_dict,
            decision=decision,
        )

    def _features_to_dict(self, bundle: FeatureBundle) -> DictLike:
        ctx = getattr(bundle, "context", None)
        ctx_dict: Dict[str, Any] = {}
        if ctx is not None:
            for key in ("symbol", "t0", "trace_id", "data_lag_min", "missing_ratio"):
                val = getattr(ctx, key, None)
                if val is not None:
                    ctx_dict[key] = val
        return {"context": ctx_dict}


__all__ = ["DecisionEngine", "DecisionRecord", "DecisionRequest", "DecisionResult"]
