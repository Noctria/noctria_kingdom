# ファイル名: path_config.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T01:04:45.033332
# 生成AI: openai_noctria_dev.py
# UUID: d5925016-395b-4e13-a165-b545a6afb937
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

```python
from pathlib import Path

# Path definitions for data sources and model outputs
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_SOURCE_URL: str = "https://example.com/data"
LOCAL_DATA_PATH: Path = PROJECT_DIR / "data" / "local_data"
FEATURES_PATH: Path = PROJECT_DIR / "data" / "features"
MODEL_PATH: Path = PROJECT_DIR / "models" / "trained_model"
```