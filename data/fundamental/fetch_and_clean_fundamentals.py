#!/usr/bin/env python3
# coding: utf-8

import pandas as pd
import requests

def fetch_fred_data(api_key, series_id):
    """
    FRED APIからデータを取得し、DataFrameに整形
    """
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json"
    }

    response = requests.get(url, params=params)
    data = response.json()["observations"]

    df = pd.DataFrame(data)
    df = df[["date", "value"]]
    df["value"] = pd.to_numeric(df["value"], errors='coerce')
    df.dropna(inplace=True)
    df["date"] = pd.to_datetime(df["date"])
    return df

def save_cleaned_data(df, output_path):
    df.to_csv(output_path, index=False)
    print(f"✅ 保存完了: {output_path}")

if __name__ == "__main__":
    api_key = "c0cb7c667f94e8ecee6a2fbc71020201"

    fundamentals = {
        "cpi": {
            "series_id": "CPIAUCSL",
            "output_path": "data/fundamental/cleaned_cpi.csv"
        },
        "interest_diff": {
            "series_id": "IR",  # 仮の例
            "output_path": "data/fundamental/cleaned_interest_diff.csv"
        },
        "unemployment": {
            "series_id": "UNRATE",
            "output_path": "data/fundamental/cleaned_unemployment.csv"
        },
        "ffr": {
            "series_id": "FEDFUNDS",
            "output_path": "data/fundamental/cleaned_ffr.csv"
        },
        "gdp": {
            "series_id": "GDP",
            "output_path": "data/fundamental/cleaned_gdp.csv"
        }
    }

    for name, info in fundamentals.items():
        df = fetch_fred_data(api_key, info["series_id"])
        save_cleaned_data(df, info["output_path"])
