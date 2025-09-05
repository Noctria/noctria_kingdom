print("=== Trade Analysis Script Started ===")

import pandas as pd
import matplotlib.pyplot as plt
import glob
import os

print("[INFO] Checking logs directory for trade history CSVs...")

file_list = sorted(glob.glob("logs/trade_history_*.csv"))
print(f"[INFO] Found files: {file_list}")

if not file_list:
    print("No trade history data found!")
    exit()

all_data = []
for file in file_list:
    print(f"[INFO] Reading file: {file}")
    df = pd.read_csv(file)
    df["file"] = file  # どの週のデータかを分かりやすくする
    all_data.append(df)

print("[INFO] Merging dataframes...")
combined_df = pd.concat(all_data, ignore_index=True)

print("[INFO] Combined DataFrame preview:")
print(combined_df.head())

# 週ごとの勝率を計算
win_rates = []
for file in combined_df["file"].unique():
    week_df = combined_df[combined_df["file"] == file]
    total = len(week_df)
    wins = week_df[week_df["profit"] > 0].shape[0]
    win_rate = wins / total if total > 0 else 0
    win_rates.append({"week": file, "win_rate": win_rate})

win_rate_df = pd.DataFrame(win_rates)

# 週次勝率の折れ線グラフを保存
plt.figure(figsize=(10, 5))
plt.plot(win_rate_df["week"], win_rate_df["win_rate"], marker='o', label="Win Rate")
plt.xticks(rotation=45)
plt.xlabel("Week")
plt.ylabel("Win Rate")
plt.title("Weekly Win Rate Over Time")
plt.legend()
plt.tight_layout()
os.makedirs("logs/plots", exist_ok=True)
plt.savefig("logs/plots/win_rate_plot.png")
print("[INFO] Win rate plot saved to logs/plots/win_rate_plot.png")

# 利益分布のヒストグラムを保存
plt.figure(figsize=(8, 4))
combined_df["profit"].hist(bins=30)
plt.xlabel("Profit")
plt.ylabel("Frequency")
plt.title("Profit Distribution")
plt.tight_layout()
plt.savefig("logs/plots/profit_distribution.png")
print("[INFO] Profit distribution plot saved to logs/plots/profit_distribution.png")

print("=== Trade Analysis Script Finished ===")
