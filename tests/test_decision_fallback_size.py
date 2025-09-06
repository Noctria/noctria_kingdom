from plan_data.run_inventor import _fallback_size

def test_fallback_size_writes_nonzero():
    decision = {"size": 0.0, "reason": ""}
    # qty=1.0, risk=0.5 相当の候補を模擬
    p = type("X", (), {"qty_raw": 1.0, "risk_score": 0.5})()
    applied = _fallback_size(decision, [p])
    assert applied is True
    assert decision["size"] > 0.0
    assert "fallback_size_applied" in decision["reason"]
