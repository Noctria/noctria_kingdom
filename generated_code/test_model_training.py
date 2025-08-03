# ファイル名: test_model_training.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T02:43:20.446702
# 生成AI: openai_noctria_dev.py
# UUID: 64cc03bf-da66-42ec-a63b-891fb17304ef
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

import pytest
import os

from generated_code.model_training import train_model
from src.core.path_config import FEATURES_PATH, MODEL_PATH

def test_train_model():
    train_model(FEATURES_PATH, MODEL_PATH)
    assert os.path.exists(MODEL_PATH)
```