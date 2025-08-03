# ファイル名: test_data_collection.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T02:49:49.009372
# 生成AI: openai_noctria_dev.py
# UUID: cbce31cd-8dbc-4465-842b-0b552f0f63fe
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

```python
import pytest
from src.core.path_config import DATA_SOURCE_URL, LOCAL_DATA_PATH

def test_data_source_url():
    assert DATA_SOURCE_URL == "https://example.com/data"

def test_local_data_path():
    assert str(LOCAL_DATA_PATH).endswith("data/local_data")
```