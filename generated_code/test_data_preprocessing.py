# ファイル名: test_data_preprocessing.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T02:12:47.573762
# 生成AI: openai_noctria_dev.py
# UUID: bd6aa4c0-14bc-4f74-a296-0b4e934b9318
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

```python
# test_data_preprocessing.py
import pandas as pd
import pytest
from data_preprocessing import DataPreprocessing

def test_load_data(monkeypatch):
    data = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})

    def mock_read_csv(*args, **kwargs):
        return data

    monkeypatch.setattr(pd, 'read_csv', mock_read_csv)
    processor = DataPreprocessing("dummy/path")
    loaded_data = processor.load_data()
    pd.testing.assert_frame_equal(loaded_data, data)

def test_clean_data():
    data = pd.DataFrame({"A": [1, 2, None], "B": [4, None, 6]})
    cleaned_data = DataPreprocessing("dummy/path").clean_data(data)
    assert cleaned_data.isnull().sum().sum() == 0
```