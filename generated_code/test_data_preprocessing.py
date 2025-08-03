# ファイル名: test_data_preprocessing.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T03:02:05.443993
# 生成AI: openai_noctria_dev.py
# UUID: f6d0720b-4ce3-4e51-968a-426c7a1f562a
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

```python
# test/test_data_preprocessing.py

import pytest
from generated_code.data_preprocessing import DataPreprocessing
from src.core.path_config import LOCAL_DATA_PATH

def test_data_preprocessing_init():
    processor = DataPreprocessing(LOCAL_DATA_PATH)
    assert processor.data_path == LOCAL_DATA_PATH

def test_load_data():
    processor = DataPreprocessing(LOCAL_DATA_PATH)
    data = processor.load_data()
    assert "data" in data
```