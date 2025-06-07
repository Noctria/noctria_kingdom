"""
integrate_fundamental_data.py
ファンダメンタルデータ（例: CPI, 金利差, 失業率など）を
テクニカルデータ（例: 1時間足OHLCV）に統合する前処理スクリプト。
"""

import pandas as pd

def integrate_fundamental_data(ohlcv_path, fund_path, output_path):
    """
    OHLCVデータとファンダメンタルデータを結合して保存する。

    Parameters:
    ----------
    ohlcv_path: str
        OHLCVデータのCSVファイルパス
    fund_path: str
        ファンダメンタルデータのCSVファイルパス
    output_path: str
        統合後のCSV出力先パス
    """
    # 1時間足OHLCVデータ（ヘッダ行あり）
    ohlcv_df = pd.read_csv(
        ohlcv_path,
        parse_dates=['Datetime']
    )

    # 列名を小文字に統一
    ohlcv_df.rename(columns={
        'Datetime': 'datetime',
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close'
    }, inplace=True)

    ohlcv_df.set_index('datetime', inplace=True)

    # ファンダメンタルデータ（例: 月次データ）
    fund_df = pd.read_csv(fund_path, parse_dates=['date'])
    fund_df.set_index('date', inplace=True)

    # 直近発表値で埋める（forward fill）
    ohlcv_df['cpi'] = fund_df['cpi'].reindex(ohlcv_df.index, method='ffill')
    ohlcv_df['interest_diff'] = fund_df['interest_diff'].reindex(ohlcv_df.index, method='ffill')
    ohlcv_df['unemployment'] = fund_df['unemployment'].reindex(ohlcv_df.index, method='ffill')

    # 保存
    ohlcv_df.to_csv(output_path)
    print(f"統合データを {output_path} に保存しました。")

if __name__ == "__main__":
    # データパス例
    ohlcv_csv = "data/preprocessed_usdjpy_1h.csv"
    fund_csv = "data/fundamental/cleaned_fred_data.csv"
    output_csv = "data/preprocessed_usdjpy_with_fundamental.csv"

    integrate_fundamental_data(ohlcv_csv, fund_csv, output_csv)
