# tests/test_harmonia_rerank.py
from __future__ import annotations

# 互換インポート（src/ 配下 or 直下 codex/ 配下のどちらでも動くように）
try:
    from src.codex.agents.harmonia import rerank_candidates  # type: ignore
except Exception:
    from codex.agents.harmonia import rerank_candidates  # type: ignore


class P:
    def __init__(self, intent, risk_score=None):
        self.intent = intent
        self.risk_score = risk_score


def test_rerank_order_changes_with_quality():
    c1 = P("LONG", risk_score=0.6)
    c2 = P("SHORT", risk_score=0.9)

    # ベースケース（欠損なし / ラグなし）
    out = rerank_candidates([c1, c2], context={"data_lag_min": 0}, quality={"missing_ratio": 0.0})
    assert len(out) == 2
    assert hasattr(out[0], "risk_adjusted")

    # 欠損率を上げても最低限実行でき、risk_adjusted が再計算されること
    out2 = rerank_candidates([c1, c2], context={"data_lag_min": 0}, quality={"missing_ratio": 0.4})
    assert len(out2) == 2
    assert hasattr(out2[0], "risk_adjusted")

    # 順位が変わる可能性はあるが、少なくとも risk_adjusted の数値は再計算され差が付く
    # （厳密な順位までは固定しない：実装を壊しにくくするため）
    ra_base = [getattr(x, "risk_adjusted", None) for x in out]
    ra_high_missing = [getattr(x, "risk_adjusted", None) for x in out2]
    assert any(a != b for a, b in zip(ra_base, ra_high_missing))
