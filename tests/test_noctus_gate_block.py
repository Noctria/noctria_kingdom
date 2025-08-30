# tests/test_noctus_gate_block.py
import pandas as pd
import pytest # conftest.py を使うために import 

# --- 修正点: 複雑なインポート処理をすべて削除し、シンプルに ---
from plan_data.contracts import FeatureBundle, StrategyProposal
from plan_data.adapter_to_decision import run_strategy_and_decide


class RiskyStrategy:
    """テスト用の高リスク提案を行う戦略クラス"""
    def propose(self, features: FeatureBundle, **kw) -> StrategyProposal:
        # Pydanticモデルからコンテキスト情報を取得
        symbol = features.context.get("symbol", "USDJPY")

        return StrategyProposal(
            symbol=symbol,
            direction="LONG",
            qty=1.0,
            confidence=0.9,
            reasons=["test risky"],
            meta={"risk_score": 0.95},
            schema_version="1.0.0",
        )


def test_noctus_gate_blocks_and_emits_alert(capture_alerts):
    """
    NoctusGateが高リスク提案をブロックし、アラートを発火させることをテストする
    """
    df = pd.DataFrame({"t": pd.to_datetime(["2025-08-01", "2025-08-02", "2025-08-03"])})

    # --- 修正点: Pydanticモデルの定義に合わせて FeatureBundle を作成 ---
    fb = FeatureBundle(
        features=df,                      # 'df' を 'features' に変更
        trace_id="test-trace-noctus-001", # トップレベルに移動
        context={
            "symbol": "GBPUSD",
            "timeframe": "1h",
            "data_lag_min": 0,
            "missing_ratio": 0.0,
        },
    )

    # 戦略実行と意思決定
    decision = run_strategy_and_decide(RiskyStrategy(), fb, conn_str=None)

    # NoctusGate でブロックされることを期待
    assert decision["decision"]["decision"]["action"] == "REJECT"

    # アラート発火を確認
    kinds = [alert.get("kind") for alert in capture_alerts]
    assert any(kind.startswith("NOCTUS") for kind in kinds)
