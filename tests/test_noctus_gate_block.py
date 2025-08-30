# tests/test_noctus_gate_block.py
import pandas as pd
import importlib.util, sys, pathlib

# --- strategy_adapter を直読みして強制登録 ---
path_sa = pathlib.Path(__file__).resolve().parents[1] / "src" / "plan_data" / "strategy_adapter.py"
spec_sa = importlib.util.spec_from_file_location("plan_data.strategy_adapter", path_sa)
sa = importlib.util.module_from_spec(spec_sa)
sys.modules["plan_data.strategy_adapter"] = sa
spec_sa.loader.exec_module(sa)

FeatureBundle = sa.FeatureBundle
StrategyProposal = sa.StrategyProposal

# --- contracts のエイリアスを strategy_adapter の dataclass に差し替え ---
import plan_data.contracts as contracts
contracts.FeatureBundle = FeatureBundle
contracts.StrategyProposal = StrategyProposal

# --- decision_engine を正しい場所からロードして差し替え ---
path_de = pathlib.Path(__file__).resolve().parents[1] / "src" / "decision" / "decision_engine.py"
spec_de = importlib.util.spec_from_file_location("decision.decision_engine", path_de)
de = importlib.util.module_from_spec(spec_de)
sys.modules["decision.decision_engine"] = de
spec_de.loader.exec_module(de)

# contracts を差し替えたので decision_engine 側にも反映
de.FeatureBundle = FeatureBundle
de.StrategyProposal = StrategyProposal

# --- adapter_to_decision を import（内部で decision_engine を使う） ---
path_ad = pathlib.Path(__file__).resolve().parents[1] / "src" / "plan_data" / "adapter_to_decision.py"
spec_ad = importlib.util.spec_from_file_location("plan_data.adapter_to_decision", path_ad)
ad = importlib.util.module_from_spec(spec_ad)
sys.modules["plan_data.adapter_to_decision"] = ad
spec_ad.loader.exec_module(ad)

run_strategy_and_decide = ad.run_strategy_and_decide


# --- テスト用 Strategy ---
class RiskyStrategy:
    def propose(self, features, **kw):
        # dict互換 or FeatureBundle互換で動くように
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


# --- 実際のテスト ---
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

    decision = run_strategy_and_decide(RiskyStrategy(), fb, conn_str=None)

    # NoctusGate でブロックされることを期待
    assert decision["decision"]["decision"]["action"] == "REJECT"

    # アラート発火を確認
    kinds = [a.get("kind") for a in capture_alerts]
    assert any(k.startswith("NOCTUS") for k in kinds)
