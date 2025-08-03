# ファイル名: test_data_collection.py
# バージョン: v0.1.0
# 生成日時: 2025-08-03T19:19:08.019360
# 生成AI: openai_noctria_dev.py
# UUID: 34e6daba-75fa-457c-9906-d6e3b71acd30
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

import pytest
import requests
from unittest.mock import patch
from data_collection import fetch_forex_data
from path_config import DATA_SOURCE_URL, LOCAL_DATA_PATH

# 目的: 正常にAPIからデータを取得して保存できることを確認する
# 期待結果: データ取得後、保存に成功
@patch('data_collection.requests.get')
def test_fetch_forex_data_success(mock_get):
    class MockResponse:
        status_code = 200
        text = "Sample data"

    mock_get.return_value = MockResponse()

    # 実行して、適切に保存されることを確認
    fetch_forex_data()  # 戻り値がないためエラーがないことを確認

    with open(LOCAL_DATA_PATH, 'r') as file:
        data = file.read()
        assert data == "Sample data"

# 目的: APIからデータ取得が失敗する場合の例外処理を確認する
# 期待結果: ConnectionErrorが発生する
@patch('data_collection.requests.get')
def test_fetch_forex_data_failure(mock_get):
    class MockResponse:
        status_code = 404
    
    mock_get.return_value = MockResponse()

    with pytest.raises(ConnectionError):
        fetch_forex_data()
```

### `test_feature_engineering.py`

```python