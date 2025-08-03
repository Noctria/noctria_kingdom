# ファイル名: test_data_collection.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T02:43:20.423833
# 生成AI: openai_noctria_dev.py
# UUID: e1aae311-2645-43af-a172-07a09df7e29f
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

import pytest
import requests

from src.core.path_config import DATA_SOURCE_URL, LOCAL_DATA_PATH

def test_data_download():
    # Test if DATA_SOURCE_URL is reachable
    response = requests.get(DATA_SOURCE_URL)
    assert response.status_code == 200

    # Test if downloaded data can be saved to LOCAL_DATA_PATH
    with open(LOCAL_DATA_PATH, 'wb') as f:
        f.write(response.content)

    assert os.path.exists(LOCAL_DATA_PATH)
```