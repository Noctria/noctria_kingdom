# ファイル名: test_feature_engineering.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T03:11:05.824438
# 生成AI: openai_noctria_dev.py
# UUID: 974f91e0-11c3-4c88-af8e-2ebe33d41e88
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

import pytest
from src.core.path_config import LOCAL_DATA_PATH, FEATURES_PATH

def test_feature_path_definitions():
    assert str(LOCAL_DATA_PATH).endswith("data/local_data.csv")
    assert str(FEATURES_PATH).endswith("data/features")
```