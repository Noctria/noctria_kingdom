# ファイル名: test_model_training.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T02:16:42.601926
# 生成AI: openai_noctria_dev.py
# UUID: 9c77a689-42c7-4934-9432-ead489193377
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

```python
# generated_code/test_model_training.py

from generated_code.model_training import train_model
from src.core.path_config import FEATURES_PATH, MODEL_PATH

def test_train_model():
    train_model(FEATURES_PATH, MODEL_PATH)
    assert MODEL_PATH.endswith('/path/to/model')
```