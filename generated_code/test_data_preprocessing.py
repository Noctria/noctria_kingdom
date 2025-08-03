import pandas as pd
from data_preprocessing import DataPreprocessing

def test_handle_missing_values():
    data = pd.DataFrame({'value': [1, None, 3, None, 5]})
    processor = DataPreprocessing()
    result = processor.handle_missing_values(data)
    expected = data.fillna(method='ffill').fillna(method='bfill')
    pd.testing.assert_frame_equal(result, expected)

def test_scale_data():
    data = pd.DataFrame({'value': [1, 2, 3, 4, 5]})
    processor = DataPreprocessing()
    result = processor.scale_data(data)
    assert result.mean().abs().max() < 1e-7  # 平均が0に近い
    assert result.std().abs().max() - 1 < 1e-7  # 標準偏差が1に近い

def test_prepare_data():
    data = pd.DataFrame({'value': [1, None, 3, None, 5]})
    processor = DataPreprocessing()
    result = processor.prepare_data(data)
    expected_data = processor.scale_data(processor.handle_missing_values(data))
    pd.testing.assert_frame_equal(result, expected_data)
