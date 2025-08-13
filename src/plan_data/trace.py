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
# Trace utilities for PLAN layer (and cross-layer use)
# - ContextVar によりスレッド/タスク安全に trace_id を保持
# - 人が追いやすい形式の ID を生成: YYYYMMDD-HHMMSS-SYMBOL-TF-<shortuuid>
# - 既存 API 互換: new_trace_id / get_trace_id / with_trace_id
# - 追加: ensure_trace_id / set_trace_id / clear_trace_id / trace_headers / is_valid_trace_id
# =============================================================================

# 現在の trace_id（スレッド/タスクローカル）
_current_trace_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "current_trace_id", default=None
)

# 受け渡し用の軽量データクラス（必要なら拡張）
@dataclass(frozen=True)
class Trace:
    id: str

# -------------------------
# 内部ユーティリティ
# -------------------------
_ID_PART_ALLOWED = re.compile(r"[A-Za-z0-9_\-]+")

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

def _ts() -> str:
    # UTCで桁揃え YYYYMMDD-HHMMSS
    return _now_utc().strftime("%Y%m%d-%H%M%S")

def _sanitize_part(s: str, *, upper: bool = False) -> str:
    # 許可文字以外を除去、必要なら大文字化。空になったら "NA" を返す。
    s = "".join(ch for ch in str(s) if _ID_PART_ALLOWED.match(ch))
    if not s:
        s = "NA"
    return s.upper() if upper else s

def _short_uuid(n: int = 8) -> str:
    return uuid.uuid4().hex[:max(4, min(n, 32))]

# -------------------------
# 生成・取得・設定 API
# -------------------------
def new_trace_id(*, symbol: str = "MULTI", timeframe: str = "1d") -> str:
    """
    追跡IDを生成。例: 20250813-123045-MULTI-1d-a1b2c3d4
    - 先頭は人間が読める UTC 日時（YYYYMMDD-HHMMSS）
    - 対象（symbol）と timeframe を含める
    - 衝突回避のため短縮UUIDを末尾に付与
    """
    safe_symbol = _sanitize_part(symbol, upper=True)
    safe_tf = _sanitize_part(timeframe, upper=False)
    return f"{_ts()}-{safe_symbol}-{safe_tf}-{_short_uuid(8)}"

def get_trace_id(default: Optional[str] = None) -> Optional[str]:
    """
    現在のコンテキストに紐づく trace_id を返す。未設定なら default を返す。
    """
    return _current_trace_id.get() or default

def ensure_trace_id(trace_id: Optional[str] = None) -> str:
    """
    与えられた trace_id を優先しつつ、無ければ現在のコンテキスト or 新規生成を返す。
    （読み取り専用・副作用なし）
    """
    return trace_id or get_trace_id() or new_trace_id()

def set_trace_id(trace_id: str) -> contextvars.Token:
    """
    現在のコンテキストに trace_id をセットして Token を返す。
    with 文を使わない一時設定に。
    """
    return _current_trace_id.set(trace_id)

def clear_trace_id() -> None:
    """
    現在のコンテキストの trace_id を None に上書きする（リセットトークンなし版）。
    """
    _current_trace_id.set(None)

def trace_headers(trace_id: Optional[str] = None) -> Dict[str, str]:
    """
    HTTP/メッセージ伝搬用ヘッダを返す。
    """
    return {"X-Trace-Id": ensure_trace_id(trace_id)}

def is_valid_trace_id(value: str) -> bool:
    """
    形式ゆるめの妥当性チェック：
    - 英数/アンダーバー/ハイフン/コロンのみを許容
    - 長さ 12〜200 程度
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
    コンテキスト内で現在の trace_id をセット/復元する。
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
    "new_trace_id",
    "get_trace_id",
    "ensure_trace_id",
    "set_trace_id",
    "clear_trace_id",
    "with_trace_id",
    "trace_headers",
    "is_valid_trace_id",
]
