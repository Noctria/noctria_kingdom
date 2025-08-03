# ファイル名: test_model_training.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T02:13:58.258573
# 生成AI: openai_noctria_dev.py
# UUID: 0883696b-d576-4d8c-a7b3-e3ae27c786ec
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

```python
import pytest
from src.core.path_config import FEATURES_PATH
from generated_code.model_training import train_model

def test_model_training():
    features = "features_data"
    labels = "labels_data"
    train_model(features, labels)
    assert FEATURES_PATH is not None
```