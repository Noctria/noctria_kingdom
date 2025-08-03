# ファイル名: data_preprocessing.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T02:48:35.521830
# 生成AI: openai_noctria_dev.py
# UUID: 2be82221-c9eb-4c5f-8048-454536a9e233
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

from sklearn.preprocessing import StandardScaler
import pandas as pd

class DataPreprocessing:
    def __init__(self):
        self.scaler = StandardScaler()

    def load_data(self, path: str) -> pd.DataFrame:
        return pd.read_csv(path)

    def preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        df_scaled = self.scaler.fit_transform(df)
        return pd.DataFrame(df_scaled, columns=df.columns)

```

```