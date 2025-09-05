import pandas as pd
from pathlib import Path
from src.core.path_config import MARKET_DATA_CSV  # ← 定数import

def load_market_data(csv_path: str = None) -> pd.DataFrame:
    """
    指定されたCSVファイル（省略時はプロジェクト既定データ）からマーケットデータを読み込むユーティリティ関数。
    :param csv_path: 読み込むCSVファイルのパス。Noneなら標準マーケットデータ
    :return: pandas DataFrame（ヘッダあり）
    """
    try:
        if csv_path is None:
            path = MARKET_DATA_CSV
        else:
            path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"指定されたCSVファイルが存在しません: {path}")

        # 最初の1行だけ取得して、'Date'列の有無を判定
        first_row = pd.read_csv(path, nrows=1)
        parse_dates = ['Date'] if 'Date' in first_row.columns else None

        df = pd.read_csv(path, parse_dates=parse_dates)

        if df.empty:
            raise ValueError("⚠️ 読み込んだCSVファイルが空です")

        required_cols = {'Close'}
        if not required_cols.issubset(df.columns):
            raise ValueError(f"⚠️ 必須カラム {required_cols} が見つかりません（存在するカラム: {list(df.columns)}）")

        print(f"✅ マーケットデータ読み込み成功: {path}（{len(df)} 行）")
        return df

    except Exception as e:
        raise RuntimeError(f"❌ マーケットデータの読み込みに失敗しました: {e}")
