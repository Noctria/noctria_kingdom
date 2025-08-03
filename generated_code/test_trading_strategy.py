import pandas as pd
from unittest.mock import patch
from trading_strategy import TradingStrategy

@patch('ml_model.VeritasModel.predict')
def test_generate_signals(mock_predict):
    mock_predict.return_value = [0.5, -0.5, 0.3, -0.1]  # Example predictions
    strategy = TradingStrategy()
    strategy.load_data()
    
    strategy.data = pd.DataFrame({
        'timestamp': [1, 2, 3, 4],
        'open': [100, 200, 300, 400],
        'high': [101, 201, 301, 401],
        'low': [99, 199, 299, 399],
        'close': [100, 200, 300, 400],
        'volume': [1000, 1000, 1000, 1000]
    })
    
    strategy.generate_signals()
    expected_signals = ['buy', 'sell', 'buy', 'sell']
    
    assert all(strategy.data['signals'] == expected_signals)

@patch('src.core.king_noctria.execute_order')
def test_execute_trades(mock_execute_order):
    mock_execute_order.return_value = True
    strategy = TradingStrategy()
    strategy.data = pd.DataFrame({
        'signals': ['buy', 'sell'],
        'close': [100, 200]
    })
    
    strategy.execute_trades()
    assert mock_execute_order.call_count == 2
