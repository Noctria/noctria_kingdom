import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 仮データの生成（30日分の1時間足、720行）
rows = 24 * 30
dates = pd.date_range(end=datetime.now(), periods=rows, freq='H')

df = pd.DataFrame({
    "Date": dates,
    "Open": np.random.uniform(130, 135, size=rows),
    "High": np.random.uniform(131, 136, size=rows),
    "Low": np.random.uniform(129, 134, size=rows),
    "Close": np.random.uniform(130, 135, size=rows),
    "Volume": np.random.randint(1000, 5000, size=rows),
    "interest_rate_diff": np.random.uniform(-0.5, 0.5, size=rows),
    "cpi_diff": np.random.uniform(-1.0, 1.0, size=rows),
    "sentiment_score": np.random.uniform(-1.0, 1.0, size=rows),
})

# 保存先（Airflow内のdataフォルダ）
df.to_csv("/opt/airflow/data/preprocessed_usdjpy_with_fundamental.csv", index=False)
print("✅ データ生成完了: preprocessed_usdjpy_with_fundamental.csv")
