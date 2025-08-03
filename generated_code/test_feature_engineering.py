# ファイル名: test_feature_engineering.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T01:41:27.144982
# 生成AI: openai_noctria_dev.py
# UUID: 7ceb129e-e2e5-4e96-99ec-88f181eb8d46
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

import pytest
from src.core.path_config import LOCAL_DATA_PATH, FEATURES_PATH


def test_feature_paths():
    assert LOCAL_DATA_PATH.exists()
    assert FEATURES_PATH.exists()

```