# ファイル名: test_data_collection.py
# バージョン: v0.1.0
# 生成日時: 2025-08-03T17:09:46.734113
# 生成AI: openai_noctria_dev.py
# UUID: e2055cfe-c8b2-46f8-b3d2-5b1a51f42fe8

import pytest
import pandas as pd
import os
from unittest.mock import patch, MagicMock
from path_config import get_path
from data_collection import fetch_market_data

@patch('ccxt.binance')
def test_fetch_market_data_success(mock_binance):
    mock_exchange = MagicMock()
    mock_exchange.fetch_ohlcv.return_value = [
        [1609459200000, 104.56, 104.57, 104.56, 104.57, 1000]
    ]
    mock_binance.return_value = mock_exchange

    storage_path = get_path('trading')
    csv_path = os.path.join(storage_path, 'market_data.csv')
    
    fetch_market_data()
    
    assert os.path.exists(csv_path)
    
    df = pd.read_csv(csv_path)
    assert not df.empty
    assert list(df.columns) == ['timestamp', 'open', 'high', 'low', 'close', 'volume']

@patch('ccxt.binance')
def test_fetch_market_data_network_error(mock_binance):
    mock_binance.side_effect = Exception('NetworkError')

    with pytest.raises(Exception):
        fetch_market_data()
```

### 2. `test_ml_model.py`
`ml_model.py`のテストです。

```python