# ファイル名: test_data_preprocessing.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T02:14:32.379621
# 生成AI: openai_noctria_dev.py
# UUID: 3f1ebe16-c0f2-4e81-85ff-69e75c1cd2cc
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

```python
from data_preprocessing import DataPreprocessing

def test_data_preprocessing() -> None:
    dp = DataPreprocessing("/path/to/data")
    dp.preprocess()
    assert dp.data_path == "/path/to/data"
```