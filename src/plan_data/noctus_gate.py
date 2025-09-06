# src/plan_data/noctus_gate.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json as _json
import sys as _sys

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


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """dict でもオブジェクトでも安全に属性/キーを読むヘルパ."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _get_meta(obj: Any) -> Dict[str, Any]:
    """proposal.meta を dict で取得（無ければ {}）"""
    m = _get(obj, "meta", {}) or {}
    try:
        return dict(m)
    except Exception:
        return {}


def _emit_alert(kind: str, message: str = "", **fields) -> None:
    """
    安全アラート送出:
      1) observability.emit_alert を試みる
      2) 常に stdout に 1行JSON を出す（tests が確実に拾える）
    """
    try:
        if hasattr(observability, "emit_alert"):
            observability.emit_alert(kind=kind, message=message, **fields)  # type: ignore
    except Exception:
        pass
    try:
        payload = {"kind": kind, "message": message}
        payload.update(fields)
        print(_json.dumps(payload, ensure_ascii=False))
        _sys.stdout.flush()
    except Exception:
        pass


def check_proposal(
    proposal: Any,
    *,
    max_lot_size: float = DEFAULT_MAX_LOT_SIZE,
    max_risk_score: float = DEFAULT_MAX_RISK_SCORE,
    conn_str: str | None = None,
) -> NoctusGateResult:
    """
    NoctusGate: 戦略提案を最終リスクゲート手前で検証する。

    チェック内容:
      - lot/size/qty が上限を超えていないか
      - risk_score（属性 or meta['risk_score']）がしきい値を超えていないか
    """
    reasons: List[str] = []
    blocked = False
    adjusted = False
    adjusted_size: Optional[float] = None

    # --- lot/size/qty チェック ---
    lot_candidates = (
        _get(proposal, "lot", None),
        _get(proposal, "size", None),
        _get(proposal, "qty", None),
    )
    lot_val: Optional[float] = None
    for cand in lot_candidates:
        if cand is not None:
            try:
                lot_val = float(cand)
                break
            except Exception:
                pass

    if lot_val is not None and lot_val > max_lot_size:
        blocked = True
        reasons.append(f"lot size {lot_val} > max_lot_size {max_lot_size}")

    # --- risk_score チェック（meta対応） ---
    meta = _get_meta(proposal)
    risk_attr = _get(proposal, "risk_score", None)
    risk_meta = meta.get("risk_score", None)
    risk_score_raw = risk_attr if risk_attr is not None else risk_meta

    risk_val: Optional[float] = None
    if risk_score_raw is not None:
        try:
            risk_val = float(risk_score_raw)
        except Exception:
            risk_val = None

    if risk_val is not None and risk_val > max_risk_score:
        blocked = True
        reasons.append(f"risk_score {risk_val:.2f} > max_risk_score {max_risk_score:.2f}")

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
        _emit_alert(
            kind="NOCTUS.BLOCK",
            message="; ".join(reasons) or "NoctusGate blocked proposal",
            severity="CRITICAL",
            trace=_get(proposal, "trace", _get(proposal, "trace_id", None)),
            details={
                "lot": lot_val,
                "max_lot_size": max_lot_size,
                "risk_score": risk_val,
                "max_risk_score": max_risk_score,
            },
            conn_str=conn_str,
        )

    return result
