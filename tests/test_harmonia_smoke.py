# tests/test_harmonia_smoke.py
from src.codex.agents.harmonia import rerank_candidates

class C:
    def __init__(self, risk_score, intent):
        self.risk_score = risk_score
        self.intent = intent

def test_rerank_long_bonus_and_quality_penalty():
    c1 = C(0.50, "SHORT")
    c2 = C(0.50, "LONG")   # +0.01 ボーナスで上位に来るはず
    ranked = rerank_candidates([c1, c2], context={"data_lag_min": 0}, quality={"missing_ratio": 0.0})
    assert ranked[0].intent in ("LONG", "BUY")

    # 欠損&ラグがあると減点が入る（risk_adjusted が下がる）
    c3 = C(0.80, "LONG")
    ranked2 = rerank_candidates([c3], context={"data_lag_min": 10}, quality={"missing_ratio": 0.3})
    assert hasattr(ranked2[0], "risk_adjusted")
    assert ranked2[0].risk_adjusted < 0.80  # ペナルティ反映
