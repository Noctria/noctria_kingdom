import pandas as pd

# strategy_adapter 版の FeatureBundle/StrategyProposal を強制的にインポート
import plan_data.strategy_adapter as sa
from plan_data.adapter_to_decision import run_strategy_and_decide

FeatureBundle = sa.FeatureBundle
StrategyProposal = sa.StrategyProposal

class RiskyStrategy:
    def propose(self, features, **kw):
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
            meta={"risk_score": 0.95},  # A案：metaにrisk_score
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

    # Decision は REJECT を期待
    assert result["decision"]["decision"]["action"] == "REJECT"

    # アラートが飛んでいること
    assert any(a.get("kind") == "NOCTUS.RISK_SCORE" for a in capture_alerts)
