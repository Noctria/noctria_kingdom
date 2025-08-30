# tests/test_noctus_gate_block.py
from __future__ import annotations
import pandas as pd

from plan_data.adapter_to_decision import run_strategy_and_decide
from plan_data.strategy_adapter import FeatureBundle, StrategyProposal

class RiskyStrategy:
    """NoctusGate 違反（risk_score 高すぎ）を起こすダミー戦略。"""
    def propose(self, features: FeatureBundle, **kw):
        return StrategyProposal(
            symbol=str(features.context.get("symbol", "USDJPY")),
            direction="LONG",
            qty=1.0,
            confidence=0.9,
            reasons=["test risky"],
            meta={},           # adapter 内で quality メタが付くこともある
            risk_score=0.95,   # DEFAULT_MAX_RISK_SCORE=0.8 を超える → ブロック
            schema_version="1.0",
        )

def test_noctus_gate_blocks_and_emits_alert(capture_alerts):
    df = pd.DataFrame({"t": pd.date_range("2025-08-01", periods=3, freq="D")})
    fb = FeatureBundle(
        df=df,
        context={
            "symbol": "GBPUSD",
            "timeframe": "1h",
            "trace_id": "test-trace-noctus-001",
            # QualityGate は通過させてもOK（missing_ratio=0）
            "data_lag_min": 0,
            "missing_ratio": 0.0,
        },
    )

    result = run_strategy_and_decide(RiskyStrategy(), fb, conn_str=None)

    # Decision は REJECT になっているはず（DecisionEngine を呼ぶ前にブロック）
    assert result["decision"]["decision"]["action"] == "REJECT"
    assert "NoctusGate blocked" in result["decision"]["reason"]

    # アラート（NOCTUS）が CRITICAL で上がっていることを確認
    assert len(capture_alerts) >= 1
    kinds = [a.get("kind") for a in capture_alerts]
    assert "NOCTUS" in kinds
    noctus_alerts = [a for a in capture_alerts if a.get("kind") == "NOCTUS"]
    assert any(a.get("severity") == "CRITICAL" for a in noctus_alerts)
