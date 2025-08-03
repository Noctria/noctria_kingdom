# ファイル名: test_data_preprocessing.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T02:49:49.014113
# 生成AI: openai_noctria_dev.py
# UUID: ffc91570-f2a3-48db-b9d7-f6276033a43c
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

```python
import pytest
from data_preprocessing import DataPreprocessing
from src.core.path_config import LOCAL_DATA_PATH

def test_data_preprocessing_initialization():
    processor = DataPreprocessing(LOCAL_DATA_PATH)
    assert processor.raw_data_path == LOCAL_DATA_PATH
```