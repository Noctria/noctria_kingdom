# ファイル名: path_config.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T01:41:27.091050
# 生成AI: openai_noctria_dev.py
# UUID: 9b21de4f-136a-4e54-8831-ac6bd4d08c0a
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Data paths
DATA_SOURCE_URL = "https://example.com/data-source"
LOCAL_DATA_PATH = BASE_DIR / "data" / "local_data"

# Feature paths
FEATURES_PATH = BASE_DIR / "data" / "features"

# Model paths
MODEL_PATH = BASE_DIR / "models" / "model.pkl"

```