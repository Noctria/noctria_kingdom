# ファイル名: test_data_collection.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T03:18:39.757346
# 生成AI: openai_noctria_dev.py
# UUID: 92f1e137-12de-49d7-9c4f-a800e6b6431a
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

```python
import pytest
from src.core.path_config import DATA_SOURCE_URL, LOCAL_DATA_PATH

def test_data_source_url_defined():
    assert DATA_SOURCE_URL is not None
    assert "http" in DATA_SOURCE_URL

def test_local_data_path_exists():
    assert LOCAL_DATA_PATH.exists()
    assert LOCAL_DATA_PATH.is_dir()
```