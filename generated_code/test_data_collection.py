# ファイル名: test_data_collection.py
# バージョン: v0.1.0
# 生成日時: 2025-08-03T17:10:43.604107
# 生成AI: openai_noctria_dev.py
# UUID: 30430b66-37a2-4dd2-a747-eba5cd3c0ec6

import pytest
import pandas as pd
import os
from unittest.mock import patch, MagicMock
from path_config import get_path
from data_collection import fetch_market_data

# Binanceのmockを利用して、マーケットデータの取得テストを行います。
@patch('ccxt.binance')
def test_fetch_market_data_success(mock_binance):
    mock_exchange = MagicMock()
    mock_exchange.fetch_ohlcv.return_value = [
        [1609459200000, 104.56, 104.57, 104.56, 104.57, 1000]
    ]
    mock_binance.return_value = mock_exchange

    # 取得したデータが正しいパスに保存されているかを確認します。
    storage_path = get_path('trading')
    csv_path = os.path.join(storage_path, 'market_data.csv')
    
    # データ収集の関数を実行
    fetch_market_data()
    
    # ファイルが存在するかを確認
    assert os.path.exists(csv_path)
    
    # 保存されたCSVファイルが空でないことを確認
    df = pd.read_csv(csv_path)
    assert not df.empty
    assert list(df.columns) == ['timestamp', 'open', 'high', 'low', 'close', 'volume']

# ネットワークエラーの場合のテストを行います。
@patch('ccxt.binance')
def test_fetch_market_data_network_error(mock_binance):
    mock_binance.side_effect = Exception('NetworkError')

    # ネットワークエラーが発生した際に例外がスローされるかを確認します。
    with pytest.raises(Exception):
        fetch_market_data()
```

このように、コードに日本語で説明を追加する際には、説明部分をすべて `#` で始めることでコメントアウトし、Pythonの構文エラーを防ぎましょう。これにより、コードの可読性も向上し、メンテナンスがしやすくなります。コメントを正しく記述した後、再度テストを実行して、エラーが解消されたかどうかを確認してください。