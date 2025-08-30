# tests/test_noctus_gate_block.py
import pandas as pd
import importlib.util, sys, pathlib

# contracts.py によるエイリアスを避けて strategy_adapter を直読みする
path = pathlib.Path(__file__).resolve().parents[1] / "src" / "plan_data" / "strategy_adapter.py"
spec = importlib.util.spec_from_file_location("plan_data.strategy_adapter", path)
sa = importlib.util.module_from_spec(spec)
sys.modules["plan_data.strategy_adapter"] = sa
spec.loader.exec_module(sa)

FeatureBundle = sa.FeatureBundle  # dataclass版
StrategyProposal = sa.StrategyProposal

from plan_data.adapter_to_decision import run_strategy_and_decide


class RiskyStrategy:
    def propose(self, features, **kw):
        """dict / dataclass FeatureBundle / Pydantic FeatureBundleV1 の全部に対応"""
        symbol = "USDJPY"

        # dict互換
        if isinstance(features, dict):
            symbol = features.get("ctx_symbol", symbol)

        # dataclass FeatureBundle
        elif hasattr(features, "context") and isinstance(features.context, dict):
            symbol = features.context.get("symbol", symbol)

        # Pydantic FeatureBundleV1
        elif hasattr(features, "context") and hasattr(features.context, "symbol"):
            symbol = getattr(features.context, "symbol", symbol)

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
    """
    NoctusGateが高リスク提案をブロックし、アラートを発火させることをテストする
    """
    df = pd.DataFrame({"t": pd.to_datetime(["2025-08-01", "2025-08-02", "2025-08-03"])})

    # 修正: dataclass版 FeatureBundle は 'df' を受け取る
    fb = FeatureBundle(
        df=df,
        context={
            "symbol": "GBPUSD",
            "timeframe": "1h",
            "data_lag_min": 0,
            "missing_ratio": 0.0,
        },
    )

    decision = run_strategy_and_decide(RiskyStrategy(), fb, conn_str=None)

    # NoctusGate でブロックされることを期待
    assert decision["decision"]["decision"]["action"] == "REJECT"

    # アラート発火を確認
    kinds = [a.get("kind") for a in capture_alerts]
    assert any(k.startswith("NOCTUS") for k in kinds)
