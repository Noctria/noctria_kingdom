# ファイル名: test_feature_engineering.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T03:18:39.765612
# 生成AI: openai_noctria_dev.py
# UUID: 5f49919e-d404-48ee-9b24-3a6b4c8829b1
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

```python
import pytest
from src.core.path_config import LOCAL_DATA_PATH, FEATURES_PATH

def test_local_data_path_exists_for_feature_engineering():
    assert LOCAL_DATA_PATH.exists()
    assert LOCAL_DATA_PATH.is_dir()

def test_features_path_exists():
    assert FEATURES_PATH.exists()
    assert FEATURES_PATH.is_dir()
```