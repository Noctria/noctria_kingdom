#!/usr/bin/env python3
# coding: utf-8

import pandas as pd
import requests

def fetch_fred_data(api_key, series_id):
    print("⚔️ Aurus: FRED APIからデータを収集中…")
    url = f"https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json"
    }

    response = requests.get(url, params=params)
    data = response.json()["observations"]

    df = pd.DataFrame(data)
    df = df[["realtime_start", "realtime_end", "date", "value"]]

    return df

def main():
    print("👑 王Noctria: Aurus、Prometheusよ、情報収集の任務を開始せよ！")
    api_key = "c0cb7c667f94e8ecee6a2fbc71020201"
    series_id = "CPIAUCNS"

    df = fetch_fred_data(api_key, series_id)

    print("⚔️ Aurus: 収集完了。データの整形を進めます。")
    df = df[df["value"] != "."]
    df["value"] = df["value"].astype(float)

    print("🔮 Prometheus: 整形完了。未来の戦略に役立てます。")
    df.to_csv("data/fundamental/cleaned_cpi.csv", index=False)

    print("✅ Aurus: data/fundamental/cleaned_cpi.csv に保存完了！")
    print("👑 王Noctria: 任務完了。次の戦略へ備えよ！")

if __name__ == "__main__":
    main()
