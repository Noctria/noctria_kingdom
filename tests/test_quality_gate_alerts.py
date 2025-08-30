import pandas as pd
import pytest
from plan_data.contracts import FeatureBundle, FeatureContext
from plan_data.quality_gate import evaluate_quality

def test_quality_gate_emits_alert_on_missing_ratio(capture_alerts):
    df = pd.DataFrame({"t": pd.date_range("2025-08-01", periods=3, freq="D")})
    fb = FeatureBundle(
        features={"shape": df.shape, "columns": list(df.columns)},
        context=FeatureContext(
            symbol="USDJPY",
            timeframe="1h",
            data_lag_min=0,
            missing_ratio=0.12,
        ),
        trace_id="test-trace-quality-001",
    )

    res = evaluate_quality(fb, conn_str=None)

    assert res.action in ("SCALE", "FLAT")
    assert not res.ok
    assert res.missing_ratio >= 0.12
    assert any(a["kind"].startswith("QUALITY") for a in capture_alerts)


def test_quality_gate_emits_alert_on_data_lag(capture_alerts):
    df = pd.DataFrame({"t": pd.date_range("2025-08-01", periods=3, freq="D")})
    fb = FeatureBundle(
        features={"shape": df.shape, "columns": list(df.columns)},
        context=FeatureContext(
            symbol="EURUSD",
            timeframe="15m",
            data_lag_min=45,
            missing_ratio=0.0,
        ),
        trace_id="test-trace-quality-002",
    )

    res = evaluate_quality(fb, conn_str=None)

    assert res.action == "FLAT"
    assert not res.ok
    assert res.data_lag_min == 45
    assert any(a["kind"].startswith("QUALITY") for a in capture_alerts)
