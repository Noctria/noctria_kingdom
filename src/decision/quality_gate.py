# src/decision/quality_gate.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import pandas as pd
import numpy as np


@dataclass(frozen=True)
class QualityAssessment:
    flat: bool
    scale: float            # 0.0..1.0
    reason: str
    missing_ratio: float
    data_lag_days: float


class DataQualityGate:
    """
    DataQualityGate（簡易版）
      - 欠損率とデータ遅延で SCALE/FLAT を決定
    ルール（初期値）:
      - missing_ratio >= 0.30 → FLAT
      - data_lag_days >= 3    → FLAT
      - それ以外 → scale = clamp(1 - 1.5*missing - 0.1*lag, 0..1)
    """

    def __init__(self, thr_missing_flat: float = 0.30, thr_lag_flat_days: float = 3.0) -> None:
        self._thr_missing = float(thr_missing_flat)
        self._thr_lag = float(thr_lag_flat_days)

    @staticmethod
    def _missing_ratio(df: Optional[pd.DataFrame]) -> float:
        if df is None or df.empty:
            return 1.0
        cols = [c for c in df.columns if c != "date"]
        if not cols:
            return 0.0
        total = len(df) * len(cols)
        if total <= 0:
            return 0.0
        return float(df[cols].isna().sum().sum()) / float(total)

    @staticmethod
    def _data_lag_days(df: pd.DataFrame) -> float:
        if "date" not in df.columns or df.empty:
            return float("inf")
        last = pd.to_datetime(df["date"], errors="coerce").dropna()
        if last.empty:
            return float("inf")
        last_dt = last.iloc[-1].to_pydatetime()
        now = datetime.now(timezone.utc)
        delta = now - last_dt.replace(tzinfo=timezone.utc)
        return max(0.0, delta.total_seconds() / 86400.0)

    @staticmethod
    def _clamp(x: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, x))

    def assess(self, df: pd.DataFrame) -> QualityAssessment:
        mr = self._missing_ratio(df)
        lag = self._data_lag_days(df)

        if mr >= self._thr_missing:
            return QualityAssessment(True, 0.0, f"missing_ratio={mr:.2f} >= {self._thr_missing:.2f}", mr, lag)
        if lag >= self._thr_lag:
            return QualityAssessment(True, 0.0, f"data_lag_days={lag:.1f} >= {self._thr_lag:.1f}", mr, lag)

        scale = self._clamp(1.0 - (1.5 * mr) - (0.1 * lag), 0.0, 1.0)
        return QualityAssessment(False, float(scale), f"ok (mr={mr:.2f}, lag={lag:.1f}d)", mr, lag)
