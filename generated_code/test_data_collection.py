# ファイル名: test_data_collection.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T02:15:09.999373
# 生成AI: openai_noctria_dev.py
# UUID: 2eeab2f0-8c8e-432c-bff8-ead90b430559
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

import pytest
from src.core.path_config import DATA_SOURCE_URL, LOCAL_DATA_PATH

def test_data_collection() -> None:
    assert DATA_SOURCE_URL == "https://example.com/data/source"
    assert LOCAL_DATA_PATH == "/data/local/data_path"
```