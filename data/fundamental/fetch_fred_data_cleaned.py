#!/usr/bin/env python3
# coding: utf-8

import pandas as pd
import requests

def fetch_fred_data(api_key, series_id):
    """
    FRED APIからデータを取得し、DataFrameに整形
    """
    url = f"https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json"
    }

    response = requests.get(url, params=params)
    data = response.json()["observations"]

    # DataFrameに整形
    df = pd.DataFrame(data)
    df = df[["realtime_start", "realtime_end", "date", "value"]]

    return df

def main():
    # FRED APIキーとシリーズID
    api_key = "YOUR_API_KEY"
    series_id = "CPIAUCNS"  # 例: 消費者物価指数

    # データ取得
    df = fetch_fred_data(api_key, series_id)

    print("=== 欠損除去前 ===")
    print(df.head())

    # ✅ 欠損値（"."）を除去
    df = df[df["value"] != "."]

    # ✅ value列をfloatに変換
    df["value"] = df["value"].astype(float)

    print("\n=== 欠損除去後 & 数値変換 ===")
    print(df.head())

    # 必要ならCSV保存
    df.to_csv("data/fundamental/cleaned_fred_data.csv", index=False)
    print("\n✅ CSV保存完了: data/fundamental/cleaned_fred_data.csv")

if __name__ == "__main__":
    main()
