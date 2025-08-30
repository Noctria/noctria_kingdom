import pandas as pd

# NoctusGate 連携は adapter を通すので strategy_adapter 版を使う
from plan_data.strategy_adapter import FeatureBundle, StrategyProposal
from plan_data.adapter_to_decision import run_strategy_and_decide

# RiskyStrategy は dict/FeatureBundle 両対応にしておく（adapterは最初にdictで呼ぶ）
class RiskyStrategy:
    def propose(self, features, **kw):
        # dict でも FeatureBundle でも取れるように分岐
        if isinstance(features, dict):
            symbol = features.get("ctx_symbol", "USDJPY")
        else:
            symbol = getattr(getattr(features, "context", {}), "get", lambda k, d=None: d)("symbol", "USDJPY")

        return StrategyProposal(
            symbol=symbol,
            direction="LONG",
            qty=1.0,
            confidence=0.9,
            reasons=["test risky"],
            # A案：risk_score は meta で渡す（adapter側の最小提案型に合わせる）
            meta={"risk_score": 0.95},
            schema_version="1.0.0",
        )

def test_noctus_gate_blocks_and_emits_alert(capture_alerts):
    df = pd.DataFrame({"t": pd.date_range("2025-08-01", periods=3, freq="D")})
    fb = FeatureBundle(
        df=df,
        context={
            "symbol": "GBPUSD",
            "timeframe": "1h",
            "trace_id": "test-trace-noctus-001",
            "data_lag_min": 0,
            "missing_ratio": 0.0,
        },
    )

    result = run_strategy_and_decide(RiskyStrategy(), fb, conn_str=None)

    # Decision は REJECT を期待（NoctusGate でブロック）
    assert result["decision"]["decision"]["action"] == "REJECT"

    # アラートが飛んでいること（A案の命名：NOCTUS.RISK_SCORE）
    assert len(capture_alerts) >= 1
    kinds = [a.get("kind") for a in capture_alerts]
    assert "NOCTUS.RISK_SCORE" in kinds
