# ファイル名: test_data_collection.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T02:42:46.440537
# 生成AI: openai_noctria_dev.py
# UUID: e35dc26c-68db-4bf0-b9c5-f6c345fbfd10
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

```python
# generated_code/test_data_collection.py

import pytest
from src.core.path_config import DATA_SOURCE_URL, LOCAL_DATA_PATH

def test_data_source_url():
    assert DATA_SOURCE_URL.startswith("https://"), "DATA_SOURCE_URL should start with https://"

def test_local_data_path():
    assert LOCAL_DATA_PATH.endswith("/"), "LOCAL_DATA_PATH should end with /"
```