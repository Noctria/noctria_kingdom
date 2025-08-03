# ファイル名: test_feature_engineering.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T02:49:49.018717
# 生成AI: openai_noctria_dev.py
# UUID: ee3efeb4-9328-419e-890d-128995b7bb9a
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

```python
import pytest
from src.core.path_config import LOCAL_DATA_PATH, FEATURES_PATH

def test_local_data_path():
    assert str(LOCAL_DATA_PATH).endswith("data/local_data")

def test_features_path():
    assert str(FEATURES_PATH).endswith("data/features")
```