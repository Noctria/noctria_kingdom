# ファイル名: test_data_preprocessing.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T02:48:35.536299
# 生成AI: openai_noctria_dev.py
# UUID: 74f5e1e9-8861-4ea6-b97e-8b3c3b956609
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

import pytest
import pandas as pd
from generated_code.data_preprocessing import DataPreprocessing

def test_data_preprocessing():
    dp = DataPreprocessing()
    data = pd.DataFrame({'feature1': [1, 2, 3], 'feature2': [4, 5, 6]})
    df_scaled = dp.preprocess(data)
    
    assert df_scaled is not None
    assert df_scaled.shape == data.shape

```

```