# ファイル名: path_config.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T01:06:37.132402
# 生成AI: openai_noctria_dev.py
# UUID: 4296ec11-4ecc-4326-831c-1d55ef2b89c4
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

from pathlib import Path

# 定義されているパスはここにすべて集約
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_SOURCE_URL = 'http://example.com/data-source'
LOCAL_DATA_PATH = BASE_DIR / 'data' / 'local_data.csv'
FEATURES_PATH = BASE_DIR / 'features' / 'features.csv'
MODEL_PATH = BASE_DIR / 'models' / 'model.pkl'
```

```python