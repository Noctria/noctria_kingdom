# ファイル名: test_model_training.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T01:41:27.153368
# 生成AI: openai_noctria_dev.py
# UUID: afd998ce-910c-4fa9-8d76-32548bd9500e
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

import pytest
from generated_code.model_training import train_model
from src.core.path_config import FEATURES_PATH


def test_model_training():
    result = train_model(features_path=str(FEATURES_PATH))
    assert result is not None

```