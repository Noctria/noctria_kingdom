import types
from codex.agents.harmonia import rerank_candidates

class P:
    def __init__(self, intent, risk_score=None):
        self.intent = intent
        self.risk_score = risk_score

def test_rerank_order_changes_with_quality():
    c1 = P("LONG", risk_score=0.6)
    c2 = P("SHORT", risk_score=0.9)
    out = rerank_candidates([c1, c2], context={"data_lag_min": 0}, quality={"missing_ratio": 0.0})
    # もともとc2が高いが、missing_ratio増大で相対順位が変わらないか最低限実行性を検証
    assert len(out) == 2
    assert hasattr(out[0], "risk_adjusted")
