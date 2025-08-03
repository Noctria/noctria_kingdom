# ファイル名: test_data_collection.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T02:14:53.702533
# 生成AI: openai_noctria_dev.py
# UUID: 5b714034-6c20-4f86-b66a-c961476f8e9d
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

```python
# generated_code/test_data_collection.py

import pytest
from src.core.path_config import DATA_SOURCE_URL, LOCAL_DATA_PATH

def test_paths_defined():
    assert DATA_SOURCE_URL is not None
    assert LOCAL_DATA_PATH is not None
```