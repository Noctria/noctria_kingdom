# src/plan_data/noctus_gate.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .contracts import StrategyProposal
from . import observability


@dataclass
class NoctusGateResult:
    ok: bool
    reasons: List[str] = field(default_factory=list)
    blocked: bool = False
    adjusted: bool = False
    adjusted_size: Optional[float] = None


# --- デフォルト閾値 ---
DEFAULT_MAX_LOT_SIZE = 1.0          # 1.0 ロットを超えたらエラー
DEFAULT_MAX_RISK_SCORE = 0.8        # 0.0〜1.0 のリスク指標、0.8超ならブロック


def check_proposal(
    proposal: StrategyProposal,
    *,
    max_lot_size: float = DEFAULT_MAX_LOT_SIZE,
    max_risk_score: float = DEFAULT_MAX_RISK_SCORE,
    conn_str: str | None = None,
) -> NoctusGateResult:
    """
    NoctusGate: 戦略提案を最終リスクゲート手前で検証する。

    チェック内容:
      - lot サイズが上限を超えていないか
      - 提案に risk_score が含まれている場合、しきい値を超えていないか
    """

    reasons: List[str] = []
    blocked = False
    adjusted = False
    adjusted_size: Optional[float] = None

    # --- lot size チェック ---
    lot = getattr(proposal, "lot", None) or getattr(proposal, "size", None)
    if lot is not None:
        try:
            lot_val = float(lot)
        except Exception:
            lot_val = 0.0

        if lot_val > max_lot_size:
            blocked = True
            reasons.append(f"lot size {lot_val} > max_lot_size {max_lot_size}")

    # --- risk_score チェック ---
    risk_score = getattr(proposal, "risk_score", None)
    if risk_score is not None:
        try:
            r = float(risk_score)
        except Exception:
            r = 0.0

        if r > max_risk_score:
            blocked = True
            reasons.append(f"risk_score {r:.2f} > max_risk_score {max_risk_score:.2f}")

    ok = not blocked

    result = NoctusGateResult(
        ok=ok,
        reasons=reasons,
        blocked=blocked,
        adjusted=adjusted,
        adjusted_size=adjusted_size,
    )

    # --- 可観測性: アラート出力 ---
    if not ok:
        try:
            observability.emit_alert(
                kind="NOCTUS",
                reason="; ".join(reasons) or "NoctusGate blocked proposal",
                severity="CRITICAL",
                trace_id=getattr(proposal, "trace_id", None),
                details={
                    "lot": lot,
                    "max_lot_size": max_lot_size,
                    "risk_score": risk_score,
                    "max_risk_score": max_risk_score,
                },
                conn_str=conn_str,
            )
        except Exception as e:
            import logging
            logging.getLogger("noctria.noctus_gate").warning(
                "emit_alert failed in NoctusGate: %s (trace_id=%s)", e, getattr(proposal, "trace_id", None)
            )

    return result
