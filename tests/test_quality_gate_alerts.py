import pandas as pd
from plan_data.contracts import FeatureBundle as FB, FeatureContext as FC
from plan_data.quality_gate import evaluate_quality

def _fb(symbol: str, timeframe: str, *, lag: int, miss: float, trace: str):
    df = pd.DataFrame({"t": pd.date_range("2025-08-01", periods=3, freq="D")})
    # contracts版は features/context/trace_id で作る
    return FB(
        features={"rows": len(df)},  # 最低限でOK
        context=FC(symbol=symbol, timeframe=timeframe, data_lag_min=lag, missing_ratio=miss),
        trace_id=trace,
    )

def test_quality_gate_emits_alert_on_missing_ratio(capture_alerts):
    fb = _fb("USDJPY", "1h", lag=0, miss=0.12, trace="test-trace-quality-001")
    res = evaluate_quality(fb, conn_str=None)

    assert res.action in ("SCALE", "FLAT")
    assert not res.ok
    assert res.missing_ratio >= 0.12

    # A案の命名（QUALITY.MISSING_RATIO）に合わせて検証
    assert len(capture_alerts) >= 1
    last = capture_alerts[-1]
    assert last.get("kind") == "QUALITY.MISSING_RATIO"
    assert "exceeds" in last.get("reason", "")
    assert last.get("details", {}).get("missing_ratio") >= 0.12

def test_quality_gate_emits_alert_on_data_lag(capture_alerts):
    fb = _fb("EURUSD", "15m", lag=45, miss=0.0, trace="test-trace-quality-002")
    res = evaluate_quality(fb, conn_str=None)

    assert res.action == "FLAT"
    assert not res.ok
    assert res.data_lag_min == 45

    # A案の命名（QUALITY.DATA_LAG）に合わせて検証
    assert len(capture_alerts) >= 1
    last = capture_alerts[-1]
    assert last.get("kind") == "QUALITY.DATA_LAG"
    assert "exceeds" in last.get("reason", "")
    assert last.get("details", {}).get("data_lag_min") == 45
