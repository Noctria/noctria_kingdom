# tests/test_quality_gate_alerts.py
from __future__ import annotations
import pandas as pd

from plan_data.quality_gate import evaluate_quality
from plan_data.strategy_adapter import FeatureBundle

def test_quality_gate_emits_alert_on_missing_ratio(capture_alerts):
    # missing_ratio をしきい値(0.05)より大きくして SCALE を誘発
    df = pd.DataFrame({"t": pd.date_range("2025-08-01", periods=3, freq="D")})
    fb = FeatureBundle(
        df=df,
        context={
            "symbol": "USDJPY",
            "timeframe": "1h",
            "trace_id": "test-trace-quality-001",
            "data_lag_min": 0,          # 遅延はOK
            "missing_ratio": 0.12,      # しきい値超過 → SCALE
        },
    )

    res = evaluate_quality(fb, conn_str=None)

    # 判定
    assert res.action in ("SCALE", "FLAT")
    assert not res.ok
    assert res.missing_ratio >= 0.12

    # アラート発火を検証
    assert len(capture_alerts) >= 1
    last = capture_alerts[-1]
    assert last.get("kind") == "QUALITY"
    # SCALE の場合は MEDIUM（FLAT の場合は HIGH）
    assert last.get("severity") in ("MEDIUM", "HIGH")
    details = last.get("details") or {}
    assert details.get("missing_ratio") == res.missing_ratio
    assert details.get("action") == res.action


def test_quality_gate_emits_alert_on_data_lag(capture_alerts):
    # data_lag_min を 30分しきい値超過で FLAT を誘発
    df = pd.DataFrame({"t": pd.date_range("2025-08-01", periods=3, freq="D")})
    fb = FeatureBundle(
        df=df,
        context={
            "symbol": "EURUSD",
            "timeframe": "15m",
            "trace_id": "test-trace-quality-002",
            "data_lag_min": 45,         # 30分超 → FLAT
            "missing_ratio": 0.0,
        },
    )

    res = evaluate_quality(fb, conn_str=None)

    # 判定
    assert res.action == "FLAT"
    assert not res.ok
    assert res.data_lag_min == 45

    # アラート発火を検証（FLAT は HIGH 想定）
    assert len(capture_alerts) >= 1
    last = capture_alerts[-1]
    assert last.get("kind") == "QUALITY"
    assert last.get("severity") == "HIGH"
    details = last.get("details") or {}
    assert details.get("data_lag_min") == res.data_lag_min
    assert details.get("action") == res.action
