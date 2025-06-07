"""
integrate_multiple_fundamental_data.py
複数のファンダメンタルデータ（例: CPI, 金利差, 失業率など）を
テクニカルデータ（例: 1時間足OHLCV）に統合するスクリプト。
"""

import pandas as pd

def load_fundamental_data(path, col_name):
    """
    単一ファンダ指標のCSVを読み込み、指定列名にリネームして返す。
    """
    df = pd.read_csv(path, parse_dates=['date'])
    df.rename(columns={'value': col_name}, inplace=True)
    df.set_index('date', inplace=True)
    return df

def integrate_fundamentals(ohlcv_path, fundamental_files, output_path):
    """
    複数ファンダ指標をOHLCVに統合する。

    Parameters:
    ----------
    ohlcv_path: str
        OHLCVデータのCSVファイル
    fundamental_files: dict
        {'cpi': 'path/to/cpi.csv', 'interest_diff': 'path/to/interest.csv', ...}
    output_path: str
        出力先パス
    """
    # OHLCVデータ（ヘッダあり）
    ohlcv_df = pd.read_csv(
        ohlcv_path,
        parse_dates=['Datetime']
    )
    ohlcv_df.rename(columns={
        'Datetime': 'datetime',
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close'
    }, inplace=True)
    ohlcv_df.set_index('datetime', inplace=True)

    # ファンダ指標を順に統合
    for col_name, file_path in fundamental_files.items():
        print(f"統合中: {col_name} ← {file_path}")
        fund_df = load_fundamental_data(file_path, col_name)
        ohlcv_df[col_name] = fund_df[col_name].reindex(ohlcv_df.index, method='ffill')

    # 出力
    ohlcv_df.to_csv(output_path)
    print(f"統合データを {output_path} に保存しました。")

if __name__ == "__main__":
    # OHLCVデータ
    ohlcv_csv = "data/preprocessed_usdjpy_1h.csv"

    # ファンダ指標ファイル群（必要に応じて拡張可）
    fundamental_files = {
        'cpi': 'data/fundamental/cleaned_cpi.csv',
        'interest_diff': 'data/fundamental/cleaned_interest_diff.csv',
        'unemployment': 'data/fundamental/cleaned_unemployment.csv'
    }

    output_csv = "data/preprocessed_usdjpy_with_fundamental.csv"

    integrate_fundamentals(ohlcv_csv, fundamental_files, output_csv)
