# ファイル名: test_data_preprocessing.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T03:17:56.436946
# 生成AI: openai_noctria_dev.py
# UUID: f626fcbc-e28a-4fb3-908a-617a789fe2b2
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

```python
import pytest
from data_preprocessing import DataPreprocessing
from src.core.path_config import LOCAL_DATA_PATH

def test_data_preprocessing():
    dp = DataPreprocessing(LOCAL_DATA_PATH)
    data = dp.preprocess()
    assert not data.empty
```