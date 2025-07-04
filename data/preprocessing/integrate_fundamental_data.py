"""
fetch_and_clean_fundamentals.py
FRED APIからファンダメンタル指標をダウンロードして、
「date,value」の形式に整形して保存するスクリプト。
"""

import requests
import pandas as pd

def fetch_fred_data(api_key, series_id):
    """
    FRED APIから指定シリーズIDのデータを取得する。

    Parameters:
    ----------
    api_key: str
        FREDのAPIキー
    series_id: str
        取得するFRED指標のID（例: 'CPIAUCSL'）

    Returns:
    -------
    pd.DataFrame
        日付と値のDataFrame
    """
    url = f"https://api.stlouisfed.org/fred/series/observations"
    params = {
        'series_id': series_id,
        'api_key': api_key,
        'file_type': 'json'
    }
    response = requests.get(url, params=params)
    data = response.json()['observations']

    df = pd.DataFrame(data)
    df = df[['date', 'value']]
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df.dropna(inplace=True)
    df['date'] = pd.to_datetime(df['date'])
    return df

def save_cleaned_data(df, output_path):
    """
    整形データをCSVに保存する。
    """
    df.to_csv(output_path, index=False)
    print(f"{output_path} に保存しました。")

if __name__ == "__main__":
    # FRED APIキー
    api_key = "c0cb7c667f94e8ecee6a2fbc71020201"

    # 取得する指標と出力ファイル
    fundamentals = {
        'cpi': {
            'series_id': 'CPIAUCSL',  # 米国CPI
            'output_path': 'data/fundamental/cleaned_cpi.csv'
        },
        'interest_diff': {
            'series_id': 'IR',  # 例: 政策金利差のシリーズID（仮）
            'output_path': 'data/fundamental/cleaned_interest_diff.csv'
        },
        'unemployment': {
            'series_id': 'UNRATE',  # 失業率
            'output_path': 'data/fundamental/cleaned_unemployment.csv'
        }
    }

    for name, info in fundamentals.items():
        df = fetch_fred_data(api_key, info['series_id'])
        save_cleaned_data(df, info['output_path'])
