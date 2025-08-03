# ファイル名: test_data_collection.py
# バージョン: v0.1.0
# 生成日時: 2025-08-03T14:10:14.451348
# 生成AI: openai_noctria_dev.py
# UUID: 80f24697-4d14-48ff-8b74-6087255a3deb

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

### 再確認事項

- `test_data_collection.py`のPython構文が正しいか再度確認してください。
- `path_config.py`からURLのパスを正しくインポートし、ハードコーディングされたパスを避けること。
- `pytest`で再テストし、エラーメッセージが解消されたことを確認します。

この修正により、構文エラーが解消されることを願います。もしエラーが引き続き発生する場合は、再度エラーログを確認し、他の部分での同様の問題がないかご注意ください。