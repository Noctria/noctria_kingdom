# tests/test_decision_fallback_size.py
from __future__ import annotations

# import 互換（src/ 配下 or 直下 plan_data 配下のどちらでも動くように）
try:
    from src.plan_data.run_inventor import _fallback_size  # type: ignore
except Exception:
    from plan_data.run_inventor import _fallback_size  # type: ignore


def test_fallback_size_writes_nonzero():
    decision = {"size": 0.0, "reason": ""}
    # qty=1.0, risk=0.5 相当の候補を模擬
    p = type("X", (), {"qty_raw": 1.0, "risk_score": 0.5})()
    applied = _fallback_size(decision, [p])

    assert applied is True
    assert decision["size"] > 0.0

    # 実装差異に対応（"fallback:size" or 旧互換 "fallback_size_applied"）
    reason = str(decision.get("reason", ""))
    assert ("fallback:size" in reason) or ("fallback_size_applied" in reason)
