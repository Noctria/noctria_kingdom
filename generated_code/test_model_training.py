# ファイル名: test_model_training.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T02:17:00.130463
# 生成AI: openai_noctria_dev.py
# UUID: f991fff3-03a8-406f-b98d-8215666404a8
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

```python
from src.core.path_config import FEATURES_PATH
from model_training import train_model

def test_model_training():
    assert FEATURES_PATH is not None
    train_model(FEATURES_PATH, "path/to/model_output")
```