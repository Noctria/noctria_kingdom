# ファイル名: test_data_collection.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T03:17:56.433784
# 生成AI: openai_noctria_dev.py
# UUID: d5d67696-7951-49cd-bf5a-df2db915563e
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

```python
import pytest
from src.core.path_config import DATA_SOURCE_URL, LOCAL_DATA_PATH

def test_data_paths():
    assert isinstance(DATA_SOURCE_URL, str)
    assert LOCAL_DATA_PATH.is_file()
```