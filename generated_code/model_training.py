# ファイル名: model_training.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T02:12:47.558703
# 生成AI: openai_noctria_dev.py
# UUID: ad7cbb0a-bc07-4ecf-abb4-c95c4c156fe3
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

```python
# model_training.py
from sklearn.linear_model import LinearRegression
import pandas as pd
from src.core.path_config import FEATURES_PATH, MODEL_PATH
import joblib

def train_model() -> None:
    data = pd.read_csv(FEATURES_PATH)
    X = data.drop('target', axis=1)
    y = data['target']
    model = LinearRegression()
    model.fit(X, y)
    joblib.dump(model, MODEL_PATH)
```