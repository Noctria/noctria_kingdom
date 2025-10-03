# src/core/timeutil.py
# [NOCTRIA_CORE_REQUIRED]
from __future__ import annotations

from datetime import UTC, datetime


def utcnow() -> datetime:
    """datetime.utcnow() の代替：TZ付きで現在UTCを返す。"""
    return datetime.now(UTC)
