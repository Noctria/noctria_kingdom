# ファイル名: test_feature_engineering.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T02:15:29.991023
# 生成AI: openai_noctria_dev.py
# UUID: 99f9827a-4768-4614-a422-eed4432f7b27
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

```python
# test_feature_engineering.py

from src/core.path_config import LOCAL_DATA_PATH, FEATURES_PATH

def test_feature_paths():
    assert LOCAL_DATA_PATH.exists()
    assert FEATURES_PATH.exists()
```