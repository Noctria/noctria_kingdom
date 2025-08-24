# src/plan_data/trace.py
from __future__ import annotations

import re
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

try:
    # Python 3.7+
    from contextvars import ContextVar
except Exception:
    ContextVar = None  # type: ignore[assignment]

# この会話では Python 3.12 環境なので ContextVar は利用可能なはず
_TRACE_ID: "ContextVar[Optional[str]]" = (
    ContextVar("_TRACE_ID", default=None) if ContextVar else None  # type: ignore[assignment]
)

def _sanitize(s: str, *, upper: bool = False) -> str:
    s = re.sub(r"[^0-9A-Za-z_\-]", "", str(s))
    return s.upper() if upper else s

def new_trace_id(*, symbol: str = "MULTI", timeframe: str = "1d") -> str:
    """
    UTCタイムスタンプ + シンボル + タイムフレーム + ランダム短ID で一意なトレースIDを生成。
    例: 20250824-124502-USDJPY-1d-825d0b4a
    生成後は現在のコンテキストにもバインドされ、get_trace_id() で参照できます。
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    sym = _sanitize(symbol, upper=True) or "NA"
    tf  = _sanitize(timeframe) or "NA"
    short = uuid.uuid4().hex[:8]
    tid = f"{ts}-{sym}-{tf}-{short}"
    set_trace_id(tid)
    return tid

def set_trace_id(trace_id: Optional[str]) -> None:
    """明示的にトレースIDをセット。None を渡すと解除。"""
    if _TRACE_ID is not None:
        _TRACE_ID.set(trace_id)

def get_trace_id() -> Optional[str]:
    """現在のコンテキストにバインドされたトレースIDを取得。無ければ None。"""
    if _TRACE_ID is None:
        return None
    return _TRACE_ID.get()

@contextmanager
def bind_trace_id(trace_id: str):
    """
    コンテキストマネージャで一時的にトレースIDをバインド。
    with bind_trace_id(tid):
        # このブロック内は get_trace_id() が tid を返す
    """
    if _TRACE_ID is None:
        yield
        return
    token = _TRACE_ID.set(trace_id)
    try:
        yield
    finally:
        _TRACE_ID.reset(token)

__all__ = ["new_trace_id", "set_trace_id", "get_trace_id", "bind_trace_id"]
