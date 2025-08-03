# ファイル名: model_training.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T01:05:54.971371
# 生成AI: openai_noctria_dev.py
# UUID: c18238b0-fcf4-40ea-bc51-b4f4c1302939
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

import pandas as pd
from sklearn.linear_model import LinearRegression
import joblib


def train_model(features_path: str, model_path: str) -> None:
    try:
        # Load features
        data = pd.read_pickle(features_path)

        # Assume the last column is the target and the rest are features
        X = data.iloc[:, :-1]
        y = data.iloc[:, -1]

        # Train a model
        model = LinearRegression()
        model.fit(X, y)

        # Save the trained model
        joblib.dump(model, model_path)
    except Exception as e:
        raise ValueError("Failed to train model") from e
```

```python