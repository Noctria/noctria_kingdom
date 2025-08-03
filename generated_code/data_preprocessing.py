from path_config import DATA_PATH
import pandas as pd

def load_data(source):
    # データを指定されたソースからロード
    try:
        return pd.read_csv(source)
    except Exception:
        return pd.DataFrame()  # ファイルが無い時は空DataFrame返す

def preprocess_data(data):

    if data.empty:
        return data
    # 欠損値を平均で補完（例）
    return data.fillna(data.mean(numeric_only=True))

raw_data = load_data(DATA_PATH)
cleaned_data = preprocess_data(raw_data)
