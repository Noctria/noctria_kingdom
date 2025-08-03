# ファイル名: path_config.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T01:04:10.386535
# 生成AI: openai_noctria_dev.py
# UUID: 6b6a553d-4843-498b-a187-deae34f5e19e
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

from pathlib import Path

# Base directory for data
BASE_DIR = Path("/noctria_kingdom")

# Centralized path configurations
DATA_SOURCE_URL: str = "https://example.com/data/source"
LOCAL_DATA_PATH: Path = BASE_DIR / "data/local_data"
FEATURES_PATH: Path = BASE_DIR / "data/features"
MODEL_PATH: Path = BASE_DIR / "models"

# Ensure all specified directories exist
LOCAL_DATA_PATH.mkdir(parents=True, exist_ok=True)
FEATURES_PATH.mkdir(parents=True, exist_ok=True)
MODEL_PATH.mkdir(parents=True, exist_ok=True)
```