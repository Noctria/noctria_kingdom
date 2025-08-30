# src/decision/decision_engine.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

try:
    # 正典：Plan層の contracts / gates / observability を使用
    from plan_data.contracts import FeatureBundle, StrategyProposal  # type: ignore
    from plan_data import observability  # type: ignore
    from plan_data import quality_gate as quality_gate_mod  # type: ignore
    from plan_data import noctus_gate as noctus_gate_mod  # type: ignore
except Exception:
    # 互換: 旧来の import パス（存在すれば）
    from ..plan_data.contracts import FeatureBundle, StrategyProposal  # type: ignore
    from ..plan_data import observability  # type: ignore
    from ..plan_data import quality_gate as quality_gate_mod  # type: ignore
    from ..plan_data import noctus_gate as noctus_gate_mod  # type: ignore


DictLike = Dict[str, Any]


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """obj が dict でもオブジェクトでも安全に属性を読むヘルパ."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


@dataclass
class DecisionRecord:
    trace_id: str
    engine_version: str
    strategy_name: str
    score: float
    reason: str
    features: DictLike
    decision: DictLike


class DecisionEngine:
    """
    最終意思決定エンジン（軽量版）
    - 入力: FeatureBundle + 各AIの StrategyProposal 群
    - 品質チェック（QualityGate）は Plan 側で行う前提だが、情報は受け取って理由へ反映可能
    - NoctusGate（プレ実行リスクゲート）で違反提案はブロック
    """

    def __init__(self, version: str = "DecisionEngine/1.0"):
        self.version = version

    # --- 公開エントリ ---------------------------------------------------------
    def decide(
        self,
        bundle: FeatureBundle,
        proposals: Iterable[StrategyProposal],
        *,
        quality: Optional[quality_gate_mod.QualityResult] = None,
        profiles: Optional[DictLike] = None,
        conn_str: Optional[str] = None,
    ) -> Tuple[DecisionRecord, DictLike]:
        """
        proposals から 1件選択し、NoctusGate チェックを適用して最終決定を返す。
        - quality: Plan 側の QualityGate の結果（省略可）。理由に反映。
        - profiles: 将来の重み/ロールアウト設定など（未使用なら None でOK）。
        戻り値: (DecisionRecord, decision_dict)
        """
        trace_id = _get(bundle.context, "trace_id", None) or _get(bundle, "trace_id", "N/A")

        # 1) 候補整形
        proposals_list: List[StrategyProposal] = list(proposals or [])
        if not proposals_list:
            # 候補無し → HOLD 決定
            decision = {
                "action": "HOLD",
                "reason": "no proposals",
                "size": 0.0,
                "symbol": _get(bundle.context, "symbol", "USDJPY"),
            }
            record = self._log_and_build_record(
                trace_id=trace_id,
                bundle=bundle,
                decision=decision,
                reason="no proposals",
                strategy_name="(none)",
                score=0.0,
                conn_str=conn_str,
            )
            return record, decision

        # 2) スコア最大（または先頭）を暫定採用
        best = self._pick_best(proposals_list)

        # 3) NoctusGate で実行前リスクチェック
        ng_res = noctus_gate_mod.check_proposal(best, conn_str=conn_str)
        if not ng_res.ok:
            # ブロック → REJECT 決定
            decision = {
                "action": "REJECT",
                "reason": "NoctusGate blocked: " + "; ".join(ng_res.reasons),
                "size": float(_get(best, "lot", _get(best, "size", 0.0)) or 0.0),
                "symbol": _get(best, "symbol", _get(bundle.context, "symbol", "USDJPY")),
                "proposal": self._proposal_to_dict(best),
            }
            record = self._log_and_build_record(
                trace_id=trace_id,
                bundle=bundle,
                decision=decision,
                reason=decision["reason"],
                strategy_name=str(_get(best, "name", _get(best, "strategy", "unknown"))),
                score=float(_get(best, "score", 0.0) or 0.0),
                conn_str=conn_str,
            )
            return record, decision

        # 4) 実行アクションの組み立て（BUY/SELL/HOLD などは proposal に準拠）
        action = str(_get(best, "action", _get(best, "side", "HOLD")) or "HOLD").upper()
        size = float(_get(best, "lot", _get(best, "size", 0.0)) or 0.0)
        symbol = _get(best, "symbol", _get(bundle.context, "symbol", "USDJPY"))

        reason_list: List[str] = []
        if quality is not None and not quality.ok:
            # QualityGate の結果を理由に追記
            reason_list.append(f"quality={quality.action}({', '.join(quality.reasons)})")

        decision = {
            "action": action,
            "symbol": symbol,
            "size": size,
            "proposal": self._proposal_to_dict(best),
        }
        if reason_list:
            decision["reason"] = "; ".join(reason_list)

        # 5) 決定レコードを記録
        record = self._log_and_build_record(
            trace_id=trace_id,
            bundle=bundle,
            decision=decision,
            reason=decision.get("reason", ""),
            strategy_name=str(_get(best, "name", _get(best, "strategy", "unknown"))),
            score=float(_get(best, "score", 0.0) or 0.0),
            conn_str=conn_str,
        )
        return record, decision

    # --- 内部ユーティリティ ---------------------------------------------------
    def _pick_best(self, proposals: List[StrategyProposal]) -> StrategyProposal:
        # score があれば最大、無ければ先頭
        scored = [(float(_get(p, "score", 0.0) or 0.0), idx, p) for idx, p in enumerate(proposals)]
        scored.sort(key=lambda t: t[0], reverse=True)
        return scored[0][2] if scored else proposals[0]

    def _proposal_to_dict(self, p: StrategyProposal) -> DictLike:
        if isinstance(p, dict):
            return dict(p)
        # 代表的なフィールドのみ抜粋（存在すれば）
        keys = (
            "name", "strategy", "symbol", "side", "action", "lot", "size",
            "price", "tp", "sl", "ttl", "risk_score", "score", "extra",
        )
        out = {}
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
            observability.log_decision(
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
            import logging
            logging.getLogger("noctria.decision_engine").warning(
                "log_decision failed: %s (trace_id=%s)", e, trace_id
            )
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
        # FeatureBundle(df + context) 想定。重い df はここでは落とし、ヘッダのみ。
        ctx = getattr(bundle, "context", None)
        ctx_dict = {}
        if ctx is not None:
            # よく使う情報を抜粋
            for key in ("symbol", "t0", "trace_id", "data_lag_min", "missing_ratio"):
                val = getattr(ctx, key, None)
                if val is not None:
                    ctx_dict[key] = val
        return {"context": ctx_dict}


__all__ = ["DecisionEngine", "DecisionRecord"]
