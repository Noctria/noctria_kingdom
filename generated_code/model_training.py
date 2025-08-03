# ファイル名: model_training.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T02:15:29.965969
# 生成AI: openai_noctria_dev.py
# UUID: e9be7214-be3a-4507-bd11-2df15936ef7f
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

```python
# model_training.py

import pandas as pd
from sklearn.linear_model import LinearRegression
import joblib

def train_model(features: pd.DataFrame, target: pd.Series, model_output_path: str):
    model = LinearRegression()
    model.fit(features, target)
    joblib.dump(model, model_output_path)
```