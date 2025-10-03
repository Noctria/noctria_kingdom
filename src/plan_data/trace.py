# [NOCTRIA_CORE_REQUIRED]
# src/plan_data/trace.py
from __future__ import annotations

import re
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

try:
    from contextvars import ContextVar
except Exception:  # Python <3.7 用フォールバック
    ContextVar = None  # type: ignore[assignment]

# ContextVar による trace_id バインド（Python 3.12 環境では利用可能）
_TRACE_ID: "ContextVar[Optional[str]]" = (
    ContextVar("_TRACE_ID", default=None) if ContextVar else None  # type: ignore[assignment]
)


# =============================================================================
# Utils
# =============================================================================
def _sanitize(s: str, *, upper: bool = False) -> str:
    """記号を除去し、必要なら大文字化"""
    s = re.sub(r"[^0-9A-Za-z_\-]", "", str(s))
    return s.upper() if upper else s


# =============================================================================
# Public API
# =============================================================================
def new_trace_id(*, symbol: str = "MULTI", timeframe: str = "1d") -> str:
    """
    一意な Trace ID を生成してコンテキストにバインドする。

    フォーマット:
      YYYYMMDD-HHMMSS-{SYMBOL}-{TIMEFRAME}-{RANDOMHEX}
      例: 20250925-123456-USDJPY-1h-825d0b4a

    Args:
        symbol: 通貨ペアや対象識別子
        timeframe: 足種など
    Returns:
        str: 生成された trace_id
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    sym = _sanitize(symbol, upper=True) or "NA"
    tf = _sanitize(timeframe) or "NA"
    short = uuid.uuid4().hex[:8]
    tid = f"{ts}-{sym}-{tf}-{short}"
    set_trace_id(tid)
    return tid


def set_trace_id(trace_id: Optional[str]) -> None:
    """明示的に trace_id を設定（None で解除）。"""
    if _TRACE_ID is not None:
        _TRACE_ID.set(trace_id)


def get_trace_id() -> Optional[str]:
    """現在バインドされている trace_id を取得。無ければ None。"""
    if _TRACE_ID is None:
        return None
    return _TRACE_ID.get()


@contextmanager
def bind_trace_id(trace_id: str):
    """
    コンテキストマネージャで一時的に trace_id をバインド。

    Example:
        with bind_trace_id("TEST-TRACE"):
            do_something()
    """
    if _TRACE_ID is None:
        yield
        return
    token = _TRACE_ID.set(trace_id)
    try:
        yield
    finally:
        _TRACE_ID.reset(token)


@contextmanager
def with_trace_id(trace_id: str):
    """
    `bind_trace_id` の別名（レガシー互換）。
    単純に trace_id をバインドする。
    """
    with bind_trace_id(trace_id):
        yield trace_id


__all__ = ["new_trace_id", "set_trace_id", "get_trace_id", "bind_trace_id", "with_trace_id"]
