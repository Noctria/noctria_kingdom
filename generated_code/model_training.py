# ファイル名: model_training.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T03:17:56.427458
# 生成AI: openai_noctria_dev.py
# UUID: 5321602d-36de-4f2d-bf0c-c244ac3afe7b
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

```python
import pandas as pd
from sklearn.linear_model import LinearRegression
from joblib import dump

def train_model(features_path: str, model_path: str) -> None:
    data = pd.read_csv(features_path)
    X = data.drop("target", axis=1)
    y = data["target"]
    
    model = LinearRegression()
    model.fit(X, y)
    
    dump(model, model_path)
```