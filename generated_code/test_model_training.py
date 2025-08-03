# ファイル名: test_model_training.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T03:24:14.749822
# 生成AI: openai_noctria_dev.py
# UUID: 13f5259c-5d94-4056-8d8d-8490813856bf
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

```python
# generated_code/test_model_training.py

from src.core.path_config import FEATURES_PATH, MODEL_PATH
from generated_code.model_training import train_model

def test_model_training():
    assert FEATURES_PATH is not None
    assert MODEL_PATH is not None
    train_model(FEATURES_PATH, MODEL_PATH)
```