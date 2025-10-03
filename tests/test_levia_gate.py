# tests/test_levia_gate.py
# v1.0 — Fintokeiゲートの要件テスト（HOLD/WARN/VETO）


from src.core.fintokei_rules import Plan
from src.do_layer.levia_gate import evaluate_plan_for_levia
from src.strategies.levia_tempest import LeviaTempest


def test_hold_signal_skips_gate():
    levia = LeviaTempest(price_threshold=10.0)  # ほぼ必ずHOLDになるように
    row = {
        "USDJPY_Close": 157.20,
        "USDJPY_Volume_MA5": 500,
        "USDJPY_Volatility_5d": 0.05,
        "symbol": "USDJPY",
    }
    r = levia.decide_with_gate(row, write_reports=False)
    assert r["proposal"]["signal"] == "HOLD"
    assert r["action"] == "HOLD"
    assert r["gate"]["ok"] is True  # gateは走らずOK扱い


def test_veto_when_risk_too_large():
    # 1トレード損失が資本比で上限超→VETO想定
    # (entry - sl)を広げ、lotを大きくして意図的に過大リスクにする
    plan = Plan(
        symbol="USDJPY",
        side="buy",
        entry=157.20,
        sl=155.20,  # 200 pips
        lot=2.0,  # 大きめ
        capital=100000,  # 10万
        target_profit=50000,  # 適当
        leverage=None,
    )
    rr = evaluate_plan_for_levia(plan=plan, write_reports=False)
    assert rr.ok is False
    assert rr.level in ("VETO", "WARN")  # 通常はVETOを期待
    # VETOのときは理由に「上限」「想定損失」いずれかが含まれるはず
    assert any(("上限" in s or "想定損失" in s) for s in rr.reasons)


def test_warn_allowed_policy_in_decide_with_gate():
    # decide_with_gate は既定で WARN 許容（PROCEED）ポリシー
    levia = LeviaTempest(
        price_threshold=0.0002,  # 多少動けばBUY/SELLになる程度
        default_lot=0.2,
        tp_capital_share_pct=60.0,  # わざと高めにして WARN 想定
    )
    row = {
        "USDJPY_Close": 157.20,
        "USDJPY_Volume_MA5": 500,
        "USDJPY_Volatility_5d": 0.05,
        "symbol": "USDJPY",
        "capital": 200000,  # decide_with_gate側で拾う
    }
    r = levia.decide_with_gate(row, write_reports=False)
    if r["proposal"]["signal"] in ("BUY", "SELL"):
        # WARNでもaccepted=True/PROCEEDであることを許容仕様で確認
        assert r["action"] in ("PROCEED", "BLOCK")
        if r["gate"]["level"] == "WARN":
            assert r["action"] == "PROCEED"
