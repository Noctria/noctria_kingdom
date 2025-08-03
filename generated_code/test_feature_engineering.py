import pandas as pd
from feature_engineering import calculate_technical_indicators
from path_config import LOCAL_DATA_PATH, FEATURES_PATH

def test_calculate_technical_indicators():
    data = pd.DataFrame({'Close': [i for i in range(1, 31)]})
    data.to_csv(LOCAL_DATA_PATH, index=False)

    calculate_technical_indicators()

    engineered_data = pd.read_csv(FEATURES_PATH)
    expected_sma = engineered_data['Close'].rolling(window=20).mean()
    pd.testing.assert_series_equal(engineered_data['SMA_20'], expected_sma, check_names=False)
python
