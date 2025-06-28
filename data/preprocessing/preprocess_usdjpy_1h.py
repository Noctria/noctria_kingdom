#!/usr/bin/env python3
# coding: utf-8

import pandas as pd

def main():
    file_path = "data/usdjpy_1h.csv"  # ファイルパス

    # タブ区切りで読み込み
    df = pd.read_csv(file_path, sep="\t")

    print("=== 読み込み結果 ===")
    print(df.head())
    print(f"カラム数: {len(df.columns)}")
    print(f"カラム名: {df.columns.tolist()}")

    # 必要に応じてカラム名を修正
    df.columns = ["Date", "Time", "Open", "High", "Low", "Close", "TickVol", "Vol", "Spread"]

    print("\n=== カラム名修正後 ===")
    print(df.head())

    # datetime統合
    df["Datetime"] = pd.to_datetime(df["Date"] + " " + df["Time"])
    print(df[["Datetime", "Open", "High", "Low", "Close"]].head())

    # ✅ 保存
    save_path = "data/preprocessed_usdjpy_1h.csv"
    df[["Datetime", "Open", "High", "Low", "Close"]].to_csv(save_path, index=False)
    print(f"✅ 前処理結果を保存しました: {save_path}")

if __name__ == "__main__":
    main()
