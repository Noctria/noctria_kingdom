import requests
import pandas as pd

# あなたのAPIキーをここにセット
api_key = "c0cb7c667f94e8ecee6a2fbc71020201"
series_id = "GDP"  # 例: GDPの時系列データ

url = f"https://api.stlouisfed.org/fred/series/observations"
params = {
    "series_id": series_id,
    "api_key": api_key,
    "file_type": "json"
}

response = requests.get(url, params=params)
data = response.json()

# 観測値をDataFrameに変換
observations = data["observations"]
df = pd.DataFrame(observations)
print(df.head())
