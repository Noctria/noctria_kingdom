# ファイル名: data_collection.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T02:12:47.542710
# 生成AI: openai_noctria_dev.py
# UUID: 5e733111-5766-450c-b81c-5dd087b77109
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

```python
# data_collection.py
import requests
from src.core.path_config import DATA_SOURCE_URL, LOCAL_DATA_PATH

def download_data() -> None:
    response = requests.get(DATA_SOURCE_URL)
    if response.status_code == 200:
        with open(LOCAL_DATA_PATH, 'wb') as file:
            file.write(response.content)
    else:
        raise ConnectionError(f"Failed to download data. Status code: {response.status_code}")
```