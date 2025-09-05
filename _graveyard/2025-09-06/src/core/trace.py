# src/plan_data/trace.py
from __future__ import annotations

import contextlib
import contextvars
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Dict

# =============================================================================
# Trace utilities for PLAN layer (cross-layer OK)
# - ContextVar でスレッド/タスク安全に trace_id を保持
# - 人が読める ID: YYYYMMDD-HHMMSS-SYMBOL-TF-<shortuuid>
# - 互換API: new_trace_id / get_trace_id / with_trace_id
# - 追加API: ensure_trace_id / set_trace_id / clear_trace_id /
#           trace_headers / is_valid_trace_id / now_utc / generate_trace_id
# =============================================================================

# 現在の trace_id を保持（スレッド/タスクローカル）
_current_trace_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "current_trace_id", default=None
)

@dataclass(frozen=True)
class Trace:
    id: str

# -------------------------
# 内部ユーティリティ
# -------------------------
# 許容文字：英数・アンダーバー・ハイフン
_ID_PART_CLEAN = re.compile(r"[^A-Za-z0-9_\-]+")

def now_utc() -> datetime:
    """UTC の現在時刻（datetime, tz-aware）。"""
    return datetime.now(timezone.utc)

def _ts_dash() -> str:
    """YYYYMMDD-HHMMSS 形式（ダッシュ区切り）。"""
    return now_utc().strftime("%Y%m%d-%H%M%S")

def _ts_t() -> str:
    """YYYYMMDDTHHMMSSZ 形式（互換用）。"""
    return now_utc().strftime("%Y%m%dT%H%M%SZ")

def _sanitize_part(s: str, *, upper: bool = False) -> str:
    """許可外文字を除去し、必要に応じて大文字化。空になったら 'NA'。"""
    txt = _ID_PART_CLEAN.sub("", str(s))
    if not txt:
        txt = "NA"
    return txt.upper() if upper else txt

def _short_uuid(n: int = 8) -> str:
    return uuid.uuid4().hex[:max(4, min(n, 32))]

# -------------------------
# 生成・取得・設定 API
# -------------------------
def new_trace_id(*, symbol: str = "MULTI", timeframe: str = "1d") -> str:
    """
    人が追跡しやすい ID を生成。
    例: 20250813-123045-MULTI-1d-a1b2c3d4
    """
    safe_symbol = _sanitize_part(symbol, upper=True)
    safe_tf = _sanitize_part(timeframe, upper=False)
    return f"{_ts_dash()}-{safe_symbol}-{safe_tf}-{_short_uuid(8)}"

def generate_trace_id(prefix: Optional[str] = "noctria",
                      *,
                      symbol: Optional[str] = None,
                      timeframe: Optional[str] = None) -> str:
    """
    互換API（他モジュールが期待する名称）。
    デフォルトは prefix-YYYYMMDDTHHMMSSZ-<short> 形式。
    symbol/timeframe を与えた場合は new_trace_id 形式を優先。
    """
    if symbol or timeframe:
        return new_trace_id(symbol=symbol or "MULTI", timeframe=timeframe or "1d")
    ts = _ts_t()
    short = uuid.uuid4().hex[:12]
    return f"{prefix}-{ts}-{short}" if prefix else f"{ts}-{short}"

def get_trace_id(default: Optional[str] = None) -> Optional[str]:
    """現在のコンテキストに紐づく trace_id を返す。未設定なら default。"""
    return _current_trace_id.get() or default

def ensure_trace_id(trace_id: Optional[str] = None) -> str:
    """与えられた ID を優先。無ければ現在のコンテキスト→新規生成の順。"""
    return trace_id or get_trace_id() or new_trace_id()

def set_trace_id(trace_id: str) -> contextvars.Token:
    """現在のコンテキストに trace_id をセットして Token を返す。"""
    return _current_trace_id.set(trace_id)

def clear_trace_id() -> None:
    """現在のコンテキストの trace_id を None に上書き。"""
    _current_trace_id.set(None)

def trace_headers(trace_id: Optional[str] = None) -> Dict[str, str]:
    """HTTP/メッセージ伝搬用ヘッダ。"""
    return {"X-Trace-Id": ensure_trace_id(trace_id)}

def is_valid_trace_id(value: str) -> bool:
    """
    ゆるめの妥当性チェック：
    - 英数/アンダーバー/ハイフン/コロンのみを許容
    - 長さ 12〜200
    """
    if not isinstance(value, str):
        return False
    if not (12 <= len(value) <= 200):
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9_\-:]+", value))

# -------------------------
# コンテキストマネージャ
# -------------------------
@contextlib.contextmanager
def with_trace_id(trace_id: Optional[str] = None):
    """
    コンテキスト内で trace_id をセット/復元。
    例:
      with with_trace_id(new_trace_id(symbol="USDJPY", timeframe="1h")) as tid:
          run_pipeline(tid)
    """
    token: Optional[contextvars.Token] = None
    try:
        tid = ensure_trace_id(trace_id)
        token = _current_trace_id.set(tid)
        yield tid
    finally:
        if token is not None:
            _current_trace_id.reset(token)

# -------------------------
# エクスポート
# -------------------------
__all__ = [
    "Trace",
    "now_utc",
    "new_trace_id",
    "generate_trace_id",
    "get_trace_id",
    "ensure_trace_id",
    "set_trace_id",
    "clear_trace_id",
    "with_trace_id",
    "trace_headers",
    "is_valid_trace_id",
]
