# ファイル名: test_model_training.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T03:11:05.832079
# 生成AI: openai_noctria_dev.py
# UUID: 93a5c4c7-9c6d-4614-8316-207d83304f09
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

import pytest
from generated_code.model_training import train_model
from src.core.path_config import FEATURES_PATH, MODEL_PATH

def test_train_model():
    features = [1, 2, 3]
    model_path = MODEL_PATH / "model.pkl"
    train_model(features, model_path)
    assert model_path.exists()
```