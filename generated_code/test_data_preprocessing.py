# ファイル名: test_data_preprocessing.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T01:41:27.135900
# 生成AI: openai_noctria_dev.py
# UUID: 172e15ce-04f3-44cb-9fbc-4be98fe1b39c
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

import pytest
from generated_code.data_preprocessing import DataPreprocessing
from src.core.path_config import LOCAL_DATA_PATH


def test_data_preprocessing():
    dp = DataPreprocessing(data_path=str(LOCAL_DATA_PATH))
    result = dp.preprocess()
    assert result is not None

```