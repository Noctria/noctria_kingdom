# ファイル名: model_training.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T01:06:14.851338
# 生成AI: openai_noctria_dev.py
# UUID: 5308fb24-621e-457a-8b1e-bb09ebb06878
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
import joblib

def train_model(features, target):
    X_train, X_test, y_train, y_test = train_test_split(features, target, test_size=0.2, random_state=42)
    model = LinearRegression()
    model.fit(X_train, y_train)
    joblib.dump(model, MODEL_PATH)  # Save the trained model
    return model.score(X_test, y_test)  # Return the model's performance score

```