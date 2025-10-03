# [NOCTRIA_CORE_REQUIRED]
#!/usr/bin/env python3
# coding: utf-8
"""
💂 OrderExecution (v2.1)
- King/Plan 層の公式発注クライアント。
- HTTP ブローカー API に対して安全に注文を送る。
- 監査ログは core.utils.log_execution_event に記録（DB未設定時はNO-OP）。

依存:
  - requests
  - src.core.utils (log_execution_event)
  - src.core.path_config (ensure_import_path は任意)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

# パス関連（必要なら呼び出し側で ensure_import_path() を先に行う）
from src.core.utils import log_execution_event, setup_logger

logger = setup_logger("noctria.execution.order_execution")


@dataclass
class OrderResult:
    ok: bool
    status: str
    reason: Optional[str] = None
    broker_order_id: Optional[str] = None
    response: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status,
            "reason": self.reason,
            "broker_order_id": self.broker_order_id,
            "response": self.response or {},
        }


class OrderExecution:
    """
    MT5/ブローカー連携APIの薄いクライアント。
    例:
        exec = OrderExecution(api_url="http://host.docker.internal:5001/order")
        res = exec.execute_order("USDJPY", 0.12, "buy", 157.20, stop_loss=156.70)
    """

    def __init__(
        self,
        api_url: str,
        *,
        timeout: float = 8.0,
        retries: int = 2,
        backoff_base_sec: float = 0.8,
        default_sl_required: bool = True,
        dry_run: bool = False,
    ):
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout
        self.retries = max(0, retries)
        self.backoff_base_sec = max(0.1, backoff_base_sec)
        self.default_sl_required = default_sl_required
        self.dry_run = dry_run

    # ---------------------------
    # Public API
    # ---------------------------
    def execute_order(
        self,
        *,
        symbol: str,
        lot: float,
        order_type: str,
        entry_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        decision_id: Optional[str] = None,
        caller: Optional[str] = None,
        reason: Optional[str] = None,
        run_id: Optional[str] = None,
        dag_id: Optional[str] = None,
        task_id: Optional[str] = None,
        extras: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        安全な公式発注メソッド。
        - stop_loss は原則必須（default_sl_required=Trueの場合）
        - order_type は buy/sell に正規化
        - API へ JSON POST
        - 監査ログ (execution_events) へ書き込み

        戻り値: dict(OrderResult.to_dict() + 追加メタ)
        """
        norm_side = normalize_side(order_type)
        if norm_side is None:
            return self._log_and_return(
                ok=False,
                status="rejected",
                reason=f"invalid order_type: {order_type}",
                symbol=symbol,
                action=order_type,
                qty=lot,
                price=entry_price or 0.0,
                dag_id=dag_id,
                task_id=task_id,
                run_id=run_id,
                extras=extras,
                decision_id=decision_id,
            )

        # SLガード
        if self.default_sl_required and (stop_loss is None):
            return self._log_and_return(
                ok=False,
                status="rejected",
                reason="stop_loss is required",
                symbol=symbol,
                action=norm_side,
                qty=lot,
                price=entry_price or 0.0,
                dag_id=dag_id,
                task_id=task_id,
                run_id=run_id,
                extras=extras,
                decision_id=decision_id,
            )

        payload = {
            "symbol": symbol,
            "side": norm_side,  # buy / sell
            "lot": round(float(lot), 2),
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "meta": {
                "decision_id": decision_id,
                "caller": caller,
                "reason": reason,
            },
        }

        if self.dry_run:
            logger.info("[dry_run] order payload: %s", safe_json(payload))
            return self._log_and_return(
                ok=True,
                status="simulated",
                reason="dry_run",
                symbol=symbol,
                action=norm_side,
                qty=lot,
                price=entry_price or 0.0,
                broker_order_id=None,
                extras={"dry_run": True, **(extras or {})},
                decision_id=decision_id,
                response={"payload": payload},
                dag_id=dag_id,
                task_id=task_id,
                run_id=run_id,
            )

        # 実送信（リトライ）
        last_exc: Optional[Exception] = None
        for attempt in range(self.retries + 1):
            try:
                resp = requests.post(self.api_url, json=payload, timeout=self.timeout)
                if resp.status_code >= 500:
                    raise RuntimeError(f"broker 5xx: {resp.status_code} {resp.text[:200]}")
                data = try_parse_json(resp)
                ok, status, boid, reason_text = interpret_response(resp.status_code, data)
                return self._log_and_return(
                    ok=ok,
                    status=status,
                    reason=reason_text,
                    symbol=symbol,
                    action=norm_side,
                    qty=lot,
                    price=entry_price or 0.0,
                    broker_order_id=boid,
                    response=data,
                    dag_id=dag_id,
                    task_id=task_id,
                    run_id=run_id,
                    extras=extras,
                    decision_id=decision_id,
                )
            except Exception as e:
                last_exc = e
                if attempt < self.retries:
                    wait = self.backoff_base_sec * (2**attempt)
                    logger.warning(
                        "order attempt %d failed: %s (backoff %.2fs)", attempt + 1, e, wait
                    )
                    time.sleep(wait)
                else:
                    logger.error("order failed (no more retries): %s", e)

        # ここに来たら失敗確定
        return self._log_and_return(
            ok=False,
            status="error",
            reason=str(last_exc) if last_exc else "unknown error",
            symbol=symbol,
            action=norm_side,
            qty=lot,
            price=entry_price or 0.0,
            dag_id=dag_id,
            task_id=task_id,
            run_id=run_id,
            extras=extras,
            decision_id=decision_id,
            response={"payload": payload},
        )

    # ---------------------------
    # Internals
    # ---------------------------
    def _log_and_return(
        self,
        *,
        ok: bool,
        status: str,
        reason: Optional[str],
        symbol: str,
        action: str,
        qty: float,
        price: float,
        broker_order_id: Optional[str] = None,
        response: Optional[Dict[str, Any]] = None,
        dag_id: Optional[str] = None,
        task_id: Optional[str] = None,
        run_id: Optional[str] = None,
        extras: Optional[Dict[str, Any]] = None,
        decision_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        # DBが未設定でもNO-OPで安全
        try:
            log_execution_event(
                dag_id=dag_id or "manual",
                task_id=task_id or "order_execution",
                run_id=run_id or "manual",
                symbol=symbol,
                action=action,
                qty=float(qty),
                price=float(price),
                status=status,
                broker_order_id=broker_order_id,
                latency_ms=None,
                error=None if ok else (reason or "error"),
                extras={
                    **(extras or {}),
                    "decision_id": decision_id,
                    "raw_response": response or {},
                },
                trace_id=decision_id,
            )
        except Exception as e:
            logger.debug("log_execution_event failed (ignored): %s", e)

        result = OrderResult(
            ok=ok, status=status, reason=reason, broker_order_id=broker_order_id, response=response
        ).to_dict()
        # 互換メタを少し足して返す
        result.update({"symbol": symbol, "action": action, "qty": qty, "price": price})
        return result


# ---------------------------
# helpers
# ---------------------------
def normalize_side(side: str) -> Optional[str]:
    if not side:
        return None
    s = side.strip().lower()
    if s in {"buy", "long", "b"}:
        return "buy"
    if s in {"sell", "short", "s"}:
        return "sell"
    return None


def try_parse_json(resp: requests.Response) -> Dict[str, Any]:
    try:
        return resp.json()  # type: ignore[no-any-return]
    except Exception:
        text = (resp.text or "").strip()
        return {"status_code": resp.status_code, "text": text[:400]}


def interpret_response(
    status_code: int, data: Dict[str, Any]
) -> tuple[bool, str, Optional[str], Optional[str]]:
    """
    ブローカーAPIの返却を解釈。
    期待形:
      { "status": "ok"|"rejected"|"error", "order_id": "...", "message": "..." }
    不在時はHTTPコードで推定。
    """
    status = str(data.get("status") or "").lower()
    message = (data.get("message") or data.get("reason") or "") or None
    order_id = data.get("order_id") or data.get("broker_order_id")

    if status in {"ok", "success", "executed"} and status_code in (200, 201):
        return True, "executed", str(order_id) if order_id else None, message
    if status in {"rejected", "denied"} or status_code in (400, 422):
        return False, "rejected", None, message or f"HTTP {status_code}"
    if status_code >= 500:
        return False, "error", None, message or f"HTTP {status_code}"

    # 曖昧ケース
    ok = status_code in (200, 201)
    return ok, ("executed" if ok else "error"), str(order_id) if ok and order_id else None, message


def safe_json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return str(obj)
