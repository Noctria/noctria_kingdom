from unittest.mock import patch
from strategy_execution import generate_trade_signal, execute_strategy

def test_generate_trade_signal():
    """Test signal generation."""
    predictions = [0.1, -0.1, 0.2]
    signals = generate_trade_signal(predictions)
    assert signals == ['BUY', 'SELL', 'BUY']

@patch('strategy_execution.execute_order')
def test_execute_strategy(mock_execute_order):
    """Test strategy execution."""
    signals = ['BUY', 'SELL']
    execute_strategy(signals)
    assert mock_execute_order.call_count == 2
