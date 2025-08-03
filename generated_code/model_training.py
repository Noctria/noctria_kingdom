# ファイル名: model_training.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T02:48:35.525301
# 生成AI: openai_noctria_dev.py
# UUID: b0fec8cb-1b5a-48be-ab5e-7780dd52af1a
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

import pandas as pd
from sklearn.linear_model import LogisticRegression
import joblib

def train_model(features_path: str, model_path: str) -> None:
    df = pd.read_csv(features_path)
    X = df.drop('target', axis=1)
    y = df['target']
    
    model = LogisticRegression()
    model.fit(X, y)
    joblib.dump(model, model_path)

```

```