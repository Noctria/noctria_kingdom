# ファイル名: test_data_collection.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T03:11:05.809129
# 生成AI: openai_noctria_dev.py
# UUID: 3a823581-ee8c-40ab-88fd-9d1fda66a255
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

import pytest
from src.core.path_config import DATA_SOURCE_URL, LOCAL_DATA_PATH

def test_data_path_definitions():
    assert DATA_SOURCE_URL == "http://example.com/data.csv"
    assert str(LOCAL_DATA_PATH).endswith("data/local_data.csv")
```