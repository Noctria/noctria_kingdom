import pandas as pd
from strategy_model import StrategyModel

def test_calculate_moving_averages():
    data = pd.DataFrame({'close': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]})
    model = StrategyModel(short_window=3, medium_window=5, rsi_period=14)
    result = model.calculate_moving_averages(data)
    expected_short_ma = data['close'].rolling(window=3).mean()
    expected_medium_ma = data['close'].rolling(window=5).mean()
    pd.testing.assert_series_equal(result['short_ma'], expected_short_ma)
    pd.testing.assert_series_equal(result['medium_ma'], expected_medium_ma)

def test_calculate_bollinger_bands():
    data = pd.DataFrame({'close': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]})
    model = StrategyModel(short_window=3, medium_window=5, rsi_period=14)
    result = model.calculate_bollinger_bands(data)
    expected_sma = data['close'].rolling(window=5).mean()
    expected_stddev = data['close'].rolling(window=5).std()
    expected_upper_band = expected_sma + (expected_stddev * 2)
    expected_lower_band = expected_sma - (expected_stddev * 2)
    pd.testing.assert_series_equal(result['upper_band'], expected_upper_band)
    pd.testing.assert_series_equal(result['lower_band'], expected_lower_band)

def test_calculate_rsi():
    data = pd.DataFrame({'close': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]})
    model = StrategyModel(short_window=3, medium_window=5, rsi_period=14)
    result = model.calculate_rsi(data)
