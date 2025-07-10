import pandas as pd
from pathlib import Path

def load_market_data(csv_path: str) -> pd.DataFrame:
    """
    指定されたCSVファイルからマーケットデータを読み込むユーティリティ関数。

    :param csv_path: 読み込むCSVファイルのパス
    :return: pandas DataFrame（ヘッダあり）
    """
    try:
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"指定されたCSVファイルが存在しません: {csv_path}")

        df = pd.read_csv(csv_path, parse_dates=['Date'] if 'Date' in pd.read_csv(csv_path, nrows=1).columns else None)

        if df.empty:
            raise ValueError("⚠️ 読み込んだCSVファイルが空です")

        required_cols = {'Close'}
        if not required_cols.issubset(df.columns):
            raise ValueError(f"⚠️ 必須カラム {required_cols} が見つかりません（存在するカラム: {list(df.columns)}）")

        print(f"✅ マーケットデータ読み込み成功: {csv_path}（{len(df)} 行）")
        return df

    except Exception as e:
        raise RuntimeError(f"❌ マーケットデータの読み込みに失敗しました: {e}")
