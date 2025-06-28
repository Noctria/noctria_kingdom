# /noctria_kingdom/core/market_loader.py

import pandas as pd

def load_market_data(csv_path: str) -> pd.DataFrame:
    """
    指定されたCSVファイルからマーケットデータを読み込むユーティリティ関数。
    
    :param csv_path: 読み込むCSVファイルのパス
    :return: pandas DataFrame（ヘッダあり）
    """
    try:
        df = pd.read_csv(csv_path)
        if df.empty:
            raise ValueError("⚠️ 読み込んだCSVファイルが空です")
        return df
    except Exception as e:
        raise RuntimeError(f"❌ マーケットデータの読み込みに失敗しました: {e}")
