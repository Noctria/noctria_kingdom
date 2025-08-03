# ファイル名: path_config.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T01:05:34.929760
# 生成AI: openai_noctria_dev.py
# UUID: 3d7fcc11-c88f-43fd-a166-604f0fe93c35
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

import os

# パス定義の集中管理
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
MODEL_DIR = os.path.join(BASE_DIR, 'models')

DATA_SOURCE_URL = 'http://example.com/data_source'
LOCAL_DATA_PATH = os.path.join(DATA_DIR, 'local_data.csv')
FEATURES_PATH = os.path.join(DATA_DIR, 'features.csv')
MODEL_PATH = os.path.join(MODEL_DIR, 'model.pkl')

# パス文字列は直書き禁止。他モジュールはここからimport
```

```python