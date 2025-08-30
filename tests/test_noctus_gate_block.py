import pandas as pd
import pytest
from plan_data.contracts import FeatureBundle, FeatureContext, StrategyProposal
from plan_data.adapter_to_decision import run_strategy_and_decide

class RiskyStrategy:
    def propose(self, features: FeatureBundle, **kw):
        return StrategyProposal(
            strategy="Risky",
            intent="LONG",
            qty_raw=1.0,
            confidence=0.9,
            reasons=["test risky"],
            risk_score=0.95,   # DEFAULT_MAX_RISK_SCORE=0.8 を超える → ブロック
            trace_id="test-trace-noctus-001",
        )

def test_noctus_gate_blocks_and_emits_alert(capture_alerts):
    df = pd.DataFrame({"t": pd.date_range("2025-08-01", periods=3, freq="D")})
    fb = FeatureBundle(
        features={"shape": df.shape, "columns": list(df.columns)},
        context=FeatureContext(
            symbol="GBPUSD",
            timeframe="1h",
            data_lag_min=0,
            missing_ratio=0.0,
        ),
        trace_id="test-trace-noctus-001",
    )

    result = run_strategy_and_decide(RiskyStrategy(), fb, conn_str=None)
    assert result.decision["action"] == "REJECT"
    assert any(a["kind"].startswith("NOCTUS") for a in capture_alerts)
