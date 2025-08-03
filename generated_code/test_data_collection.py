# ファイル名: test_data_collection.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T02:15:29.978238
# 生成AI: openai_noctria_dev.py
# UUID: ba7c2a0a-b1c2-4bc2-886a-29fa1a24a528
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

```python
# test_data_collection.py

import pytest
from src.core.path_config import DATA_SOURCE_URL, LOCAL_DATA_PATH

def test_data_paths():
    assert isinstance(DATA_SOURCE_URL, str)
    assert LOCAL_DATA_PATH.exists()
```