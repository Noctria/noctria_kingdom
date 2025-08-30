# tests/test_noctus_gate_block.py
import pandas as pd
import importlib.util, sys, pathlib

# 強制的に strategy_adapter を先に読み込ませる
path = pathlib.Path(__file__).resolve().parents[1] / "src" / "plan_data" / "strategy_adapter.py"
spec = importlib.util.spec_from_file_location("plan_data.strategy_adapter", path)
sa = importlib.util.module_from_spec(spec)
sys.modules["plan_data.strategy_adapter"] = sa
spec.loader.exec_module(sa)

FeatureBundle = sa.FeatureBundle
StrategyProposal = sa.StrategyProposal

# adapter_to_decision を読む前に、内部で使う FeatureBundle を差し替える
import plan_data.adapter_to_decision as ad
ad.FeatureBundle = FeatureBundle  # 強制上書き

from plan_data.adapter_to_decision import run_strategy_and_decide


class RiskyStrategy:
    def propose(self, features, **kw):
        symbol = "USDJPY"
        if isinstance(features, dict):
            symbol = features.get("ctx_symbol", "USDJPY")
        elif hasattr(features, "context"):
            symbol = features.context.get("symbol", "USDJPY")

        return StrategyProposal(
            symbol=symbol,
            direction="LONG",
            qty=1.0,
            confidence=0.9,
            reasons=["test risky"],
            meta={"risk_score": 0.95},  # A案: risk_score は meta に入れる
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

    record, decision = run_strategy_and_decide(RiskyStrategy(), fb, conn_str=None)

    # NoctusGate でブロックされることを期待
    assert decision["action"] == "REJECT"

    # アラート発火を確認
    kinds = [a.get("kind") for a in capture_alerts]
    assert any(k.startswith("NOCTUS") for k in kinds)
