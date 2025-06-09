#!/usr/bin/env python3
# coding: utf-8

import pandas as pd
import matplotlib.pyplot as plt

def main():
    # トレード履歴ファイル
    file_path = "logs/trade_history_2025-05-31_to_2025-06-07.csv"
    
    # CSV読み込み
    df = pd.read_csv(file_path)
    
    # 日付でソート（もし必要なら）
    df = df.sort_values("deal")
    
    # 累積損益を計算
    df["cumulative_profit"] = df["profit"].cumsum()
    
    # グラフ描画
    plt.figure(figsize=(10, 6))
    plt.plot(df["deal"], df["cumulative_profit"], marker='o', label="累積利益")
    plt.xlabel("取引番号")
    plt.ylabel("累積利益")
    plt.title("Noctria Kingdom: 累積利益の推移")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    
    # 画像保存
    plt.savefig("logs/cumulative_profit.png")
    print("✅ グラフを logs/cumulative_profit.png に保存しました。")

if __name__ == "__main__":
    main()
