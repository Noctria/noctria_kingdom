#!/usr/bin/env python3
# coding: utf-8

import pandas as pd
import matplotlib.pyplot as plt

def main():
    file_path = "logs/trade_history_2025-05-31_to_2025-06-07.csv"
    print("👑 王Noctria: 我が王国の戦果を視覚に刻み込もうぞ。")

    try:
        df = pd.read_csv(file_path)
        print(f"📜 王Noctria: 履歴の書『{file_path}』を開封した。")
    except FileNotFoundError:
        print(f"⚠️ 書が見つかりませぬ: {file_path}")
        return

    df = df.sort_values("deal")
    df["cumulative_profit"] = df["profit"].cumsum()

    plt.figure(figsize=(10, 6))
    plt.plot(df["deal"], df["cumulative_profit"], marker='o', label="累積利益")
    plt.xlabel("取引番号")
    plt.ylabel("累積利益")
    plt.title("Noctria Kingdom: 累積利益の推移")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    plt.savefig("logs/cumulative_profit.png")
    print("🖼️ Prometheus: グラフ描画完了。戦果の軌跡が浮かび上がりました。")
    print("✅ 王Noctria: グラフを logs/cumulative_profit.png に保存した。王国の歩みを称えよ！")

if __name__ == "__main__":
    main()
