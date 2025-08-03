# ファイル名: test_model_training.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T03:17:56.443272
# 生成AI: openai_noctria_dev.py
# UUID: 8817ac65-46ee-4f52-9ec6-d4732fb4c140
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

```python
import pytest
from model_training import train_model
from src.core.path_config import FEATURES_PATH, MODEL_PATH

def test_model_training():
    train_model(FEATURES_PATH, MODEL_PATH)
    assert MODEL_PATH.is_file()
```