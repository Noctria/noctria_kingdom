# ファイル名: test_data_preprocessing.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T02:43:20.431704
# 生成AI: openai_noctria_dev.py
# UUID: 1919d198-9c9a-408e-9eb0-e39aff77ab98
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

import pytest
import pandas as pd

from generated_code.data_preprocessing import DataPreprocessing
from src.core.path_config import LOCAL_DATA_PATH

def test_load_data():
    dp = DataPreprocessing(LOCAL_DATA_PATH)
    data = dp.load_data()
    assert isinstance(data, pd.DataFrame)
    assert not data.empty

def test_clean_data():
    dp = DataPreprocessing(LOCAL_DATA_PATH)
    data = dp.load_data()
    cleaned_data = dp.clean_data(data)
    assert cleaned_data.isnull().sum().sum() == 0
```