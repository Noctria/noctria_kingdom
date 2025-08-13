# src/execution/risk_gate.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime, time, timezone

from src.plan_data.observability import log_alert
from src.plan_data.contracts import OrderRequest  # 既存の契約

@dataclass
class GateResult:
    order: OrderRequest
    alerts: List[Dict[str, Any]]

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

def _in_trading_hours_utc(now: datetime, windows: List[str]) -> bool:
    if not windows:
        return True
    t = now.timetz()
    for w in windows:
        try:
            s, e = w.split("-")
            ts = time.fromisoformat(s)
            te = time.fromisoformat(e)
            if ts <= t <= te:
                return True
        except Exception:
            continue
    return False

def _emit(policy: str, reason: str, severity: str, trace_id: Optional[str], details: Dict[str, Any], conn_str: Optional[str]) -> Dict[str, Any]:
    log_alert(policy_name=policy, reason=reason, severity=severity, details=details, trace_id=trace_id, conn_str=conn_str)
    return {"policy": policy, "reason": reason, "severity": severity, "details": details}

def apply_risk_policy(
    *,
    order: OrderRequest,
    policy: Dict[str, Any],
    trace_id: Optional[str],
    conn_str: Optional[str] = None,
    current_position_notional: float = 0.0,
    recent_consecutive_losses: int = 0,
) -> GateResult:
    """
    最小 Noctus Gate：
      - forbidden_symbols: 完全ブロック（FLAT）
      - trading_hours_utc: 時間外は FLAT
      - max_order_qty: qty を clamp
      - max_position_notional: (簡易) qty を総額とみなし上限調整
      - max_consecutive_losses: 超過時は shrink_after_losses_pct% に縮小
    介入は obs_alerts に記録。
    """
    default = (policy or {}).get("default", {})
    overrides = (policy or {}).get("overrides", {})
    symbol = getattr(order, "symbol", None)
    sym_pol = {**default, **(overrides.get(symbol, {}) if symbol else {})}

    alerts: List[Dict[str, Any]] = []
    qty = float(getattr(order, "qty", 0.0) or 0.0)
    side = getattr(order, "intent", "FLAT")
    now = _utc_now()

    # 禁止シンボル
    if symbol in set(sym_pol.get("forbidden_symbols", []) or []):
        alerts.append(_emit("risk.forbidden_symbol", f"forbidden symbol: {symbol}", "HIGH", trace_id, {"symbol": symbol}, conn_str))
        return GateResult(order=OrderRequest(symbol=symbol, intent="FLAT", qty=0.0, sources=getattr(order, "sources", []), trace_id=getattr(order, "trace_id", trace_id)), alerts=alerts)

    # 取引時間帯（UTC）
    windows = list(sym_pol.get("trading_hours_utc", []) or [])
    if windows and not _in_trading_hours_utc(now, windows):
        alerts.append(_emit("risk.trading_window", f"outside trading hours (utc): now={now.isoformat()} windows={windows}", "MEDIUM", trace_id, {"now": now.isoformat(), "windows": windows}, conn_str))
        return GateResult(order=OrderRequest(symbol=symbol, intent="FLAT", qty=0.0, sources=getattr(order, "sources", []), trace_id=getattr(order, "trace_id", trace_id)), alerts=alerts)

    # 連敗縮小
    max_losses = int(sym_pol.get("max_consecutive_losses", 0) or 0)
    if max_losses and recent_consecutive_losses >= max_losses and qty > 0:
        shrink_pct = float(sym_pol.get("shrink_after_losses_pct", 50) or 50) / 100.0
        new_qty = max(0.0, qty * shrink_pct)
        if new_qty < qty:
            alerts.append(_emit("risk.consecutive_losses", f"shrink qty after {recent_consecutive_losses} losses -> {int(shrink_pct*100)}%", "LOW", trace_id, {"before": qty, "after": new_qty, "losses": recent_consecutive_losses}, conn_str))
            qty = new_qty

    # 注文数量の上限
    max_order_qty = sym_pol.get("max_order_qty")
    if max_order_qty is not None and qty > float(max_order_qty):
        alerts.append(_emit("risk.max_order_qty", f"qty clamped: {qty} -> {max_order_qty}", "MEDIUM", trace_id, {"before": qty, "after": float(max_order_qty)}, conn_str))
        qty = float(max_order_qty)

    # ポジション総額（簡易）
    max_position_notional = sym_pol.get("max_position_notional")
    if max_position_notional is not None:
        projected = current_position_notional + qty
        if projected > float(max_position_notional):
            allowed = max(0.0, float(max_position_notional) - current_position_notional)
            alerts.append(_emit("risk.max_position_notional", f"qty adjusted for notional cap: {qty} -> {allowed} (cap={max_position_notional}, cur={current_position_notional})", "HIGH", trace_id, {"before": qty, "after": allowed, "cap": float(max_position_notional), "current": current_position_notional}, conn_str))
            qty = allowed

    new_order = OrderRequest(
        symbol=symbol,
        intent=side,
        qty=qty,
        order_type=getattr(order, "order_type", "MARKET"),
        limit_price=getattr(order, "limit_price", None),
        sources=getattr(order, "sources", []),
        trace_id=getattr(order, "trace_id", trace_id),
    )
    return GateResult(order=new_order, alerts=alerts)
