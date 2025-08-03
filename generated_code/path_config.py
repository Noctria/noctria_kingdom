# ファイル名: path_config.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T01:06:14.822182
# 生成AI: openai_noctria_dev.py
# UUID: d2cbbd40-1084-4734-b14b-b623102f215d
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

from pathlib import Path

BASE_DIR = Path("/path/to/your/project")

DATA_SOURCE_URL = "http://example.com/data/source"
LOCAL_DATA_PATH = BASE_DIR / "data" / "local_data"
FEATURES_PATH = BASE_DIR / "data" / "features"
MODEL_PATH = BASE_DIR / "models"

```