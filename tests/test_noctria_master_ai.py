# tests/test_noctria_master_ai.py
import numpy as np
import pytest
from strategies.Noctria import NoctriaMasterAI

@pytest.fixture
def noctria_env():
    # 王のインスタンスを初期化
    return NoctriaMasterAI()

def test_decide_action_runs(noctria_env):
    # ダミーの状態（12次元）を与えて、行動を決定させる
    dummy_state = np.random.rand(12)
    action = noctria_env.decide_action(dummy_state)
    assert action in [0, 1, 2], f"Invalid action: {action}"

def test_forecast_runs(noctria_env):
    # 未来予測機能テスト（ダミーデータ30x6次元）
    dummy_data = np.random.rand(30, 6)
    prediction = noctria_env.predict_future_market(dummy_data)
    assert isinstance(prediction, float), f"Unexpected prediction: {prediction}"

def test_risk_adjustment_runs(noctria_env):
    # 異常検知・リスク調整のテスト
    dummy_market_data = {
        "price": 100,
        "volume": 1000,
        "trend_strength": 0.5,
        "volatility": 0.2,
        "institutional_flow": 100
    }
    decision = noctria_env.adjust_risk_strategy(dummy_market_data)
    assert decision in ["REDUCE_POSITION", "NORMAL_TRADING"], f"Unexpected: {decision}"
