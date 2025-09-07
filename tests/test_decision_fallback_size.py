# tests/test_decision_fallback_size.py
from plan_data.run_inventor import _fallback_size


def test_fallback_size_writes_nonzero():
    decision = {"size": 0.0, "reason": ""}
    # qty=1.0, risk_score=0.5 の候補を模擬
    class P:
        qty_raw = 1.0
        risk_score = 0.5

    applied = _fallback_size(decision, [P()])
    assert applied is True
    assert decision["size"] > 0.0
    # 実装は "fallback:size" を理由に付与するので、それを確認
    assert "fallback:size" in decision["reason"]
