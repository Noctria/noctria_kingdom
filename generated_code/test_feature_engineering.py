# ファイル名: test_feature_engineering.py
# バージョン: v0.1.0
# 生成日時: 2025-08-03T19:19:08.026108
# 生成AI: openai_noctria_dev.py
# UUID: a34f3d42-af96-4f98-ba08-ab1c6a8e0eae
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

import pytest
import pandas as pd
from feature_engineering import calculate_technical_indicators
from path_config import LOCAL_DATA_PATH, FEATURES_PATH

# 目的: 移動平均が正しく計算されていることを確認する
# 期待結果: 出力CSVにSMA_20列が含まれ、計算結果が一致する
def test_calculate_technical_indicators():
    data = pd.DataFrame({'Close': [i for i in range(1, 31)]})
    data.to_csv(LOCAL_DATA_PATH, index=False)

    calculate_technical_indicators()

    engineered_data = pd.read_csv(FEATURES_PATH)
    expected_sma = engineered_data['Close'].rolling(window=20).mean()
    pd.testing.assert_series_equal(engineered_data['SMA_20'], expected_sma, check_names=False)
```

### `test_model_training.py`

```python