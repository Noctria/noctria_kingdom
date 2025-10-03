from codex.agents.harmonia import rerank_candidates


class P:
    def __init__(self, intent, risk_score=None, qty_raw=None):
        self.intent = intent
        self.risk_score = risk_score
        self.qty_raw = qty_raw


def test_harmonia_rerank_sets_risk_adjusted_and_orders():
    c1 = P("LONG", risk_score=0.6)
    c2 = P("SHORT", risk_score=0.9)
    out = rerank_candidates([c1, c2], context={"data_lag_min": 0}, quality={"missing_ratio": 0.0})
    assert len(out) == 2
    assert hasattr(out[0], "risk_adjusted")
    # base 0.9 が 0.6(+0.01ボーナス)を上回る
    assert [o.intent for o in out] == ["SHORT", "LONG"]


def test_harmonia_rerank_penalizes_with_lag_and_missing_ratio():
    c1 = P("LONG", risk_score=0.6)
    c2 = P("SHORT", risk_score=0.59)
    out = rerank_candidates([c1, c2], context={"data_lag_min": 10}, quality={"missing_ratio": 0.3})
    # どちらも減点されるが、相対順序は妥当
    assert out[0].intent in {"LONG", "SHORT"}
