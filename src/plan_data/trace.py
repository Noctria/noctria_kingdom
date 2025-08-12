# src/plan_data/trace.py
from __future__ import annotations

import os
import time
import uuid
import contextlib
import contextvars
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

# 実行スレッド/タスク間で安全に持てる現在の trace_id
_current_trace_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "current_trace_id", default=None
)

@dataclass(frozen=True)
class Trace:
    id: str

def _ts() -> str:
    # UTCで桁揃え YYYYMMDD-HHMMSS
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

def new_trace_id(*, symbol: str = "MULTI", timeframe: str = "1d") -> str:
    """
    追跡IDを生成。例: 20250813-123045-MULTI-1d-a1b2c3d4
    - 人が目で追いやすい先頭（日時/対象）
    - 後半に短縮UUIDで衝突回避
    """
    short = uuid.uuid4().hex[:8]
    safe_symbol = "".join(ch for ch in str(symbol) if ch.isalnum() or ch in ("-", "_")).upper()
    safe_tf = "".join(ch for ch in str(timeframe) if ch.isalnum() or ch in ("-", "_"))
    return f"{_ts()}-{safe_symbol}-{safe_tf}-{short}"

def get_trace_id(default: Optional[str] = None) -> Optional[str]:
    return _current_trace_id.get() or default

@contextlib.contextmanager
def with_trace_id(trace_id: Optional[str] = None):
    """
    コンテキスト内で現在の trace_id をセット/復元する。
    例:
      with with_trace_id(new_trace_id(symbol="USDJPY", timeframe="1h")):
          run_pipeline()
    """
    token = None
    try:
        if trace_id is None:
            trace_id = new_trace_id()
        token = _current_trace_id.set(trace_id)
        yield trace_id
    finally:
        if token is not None:
            _current_trace_id.reset(token)
