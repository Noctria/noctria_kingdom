# ファイル名: test_data_collection.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T02:12:47.568690
# 生成AI: openai_noctria_dev.py
# UUID: d12b0e9c-b2c3-4565-9e69-b2802f67b4b6
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

```python
# test_data_collection.py
import pytest
from data_collection import download_data
from src.core.path_config import LOCAL_DATA_PATH

def test_download_data(monkeypatch):
    def mock_get(url):
        class MockResponse:
            status_code = 200

            @staticmethod
            def content():
                return b'test data'

        return MockResponse()

    monkeypatch.setattr('requests.get', mock_get)
    download_data()
    with open(LOCAL_DATA_PATH, 'rb') as file:
        data = file.read()
    assert data == b'test data'
```