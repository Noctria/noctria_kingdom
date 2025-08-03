# ファイル名: test_data_collection.py
# バージョン: v0.1.0
# 生成日時: 2025-08-03T14:09:29.675735
# 生成AI: openai_noctria_dev.py
# UUID: d25adc24-44d5-4230-a1e7-a5159bd47bb3

import pytest
import pandas as pd
from unittest.mock import patch, Mock
from data_collection import fetch_usd_jpy_data, process_data
from path_config import DATA_SOURCE_URL

def test_fetch_usd_jpy_data_success():
    """Test successful data fetching."""
    with patch('data_collection.requests.get') as mock_get:
        mock_get.return_value = Mock(status_code=200, json=lambda: [{'date': '2023-01-01', 'price': 135}])
        df = fetch_usd_jpy_data()
        assert not df.empty
        assert 'price' in df.columns

def test_fetch_usd_jpy_data_failure():
    """Test data fetching failure."""
    with patch('data_collection.requests.get') as mock_get:
        mock_get.return_value.raise_for_status.side_effect = Exception('Error fetching data')
        with pytest.raises(Exception):
            fetch_usd_jpy_data()

def test_process_data():
    """Test data processing."""
    data = {'date': ['2023-01-01'], 'price': [135]}
    df = pd.DataFrame(data)
    processed_df = process_data(df)
    assert 'normalized_price' in processed_df.columns
    assert not processed_df.empty
```

### 2. モデル設計・トレーニングのテスト

#### test_model_design.py
```python