# ファイル名: test_model_training.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T02:58:22.509069
# 生成AI: openai_noctria_dev.py
# UUID: d82b0061-1fe7-4a25-804f-fe9cc3c13bf1
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

```python
import pytest
from generated_code.model_training import train_model
from src.core.path_config import FEATURES_PATH, MODEL_PATH

def test_train_model(tmp_path):
    model_output_path = tmp_path / "model.txt"
    train_model(FEATURES_PATH, model_output_path)
    assert model_output_path.read_text() == f"Trained model using features from {FEATURES_PATH}"
```