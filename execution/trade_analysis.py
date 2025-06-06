import pandas as pd
import matplotlib.pyplot as plt
import glob

def visualize_trade_history():
    # 直近の全週次レポートを集める
    file_list = sorted(glob.glob("logs/trade_history_*.csv"))
    all_data = []
    for file in file_list:
        df = pd.read_csv(file)
        df["file"] = file  # どの週かわかるようにファイル名を記録
        all_data.append(df)

    if not all_data:
        print("No trade history data found!")
        return

    combined_df = pd.concat(all_data, ignore_index=True)

    # 週ごとの勝率を計算
    win_rates = []
    for file in combined_df["file"].unique():
        week_df = combined_df[combined_df["file"] == file]
        total = len(week_df)
        wins = week_df[week_df["profit"] > 0].shape[0]
        win_rate = wins / total if total > 0 else 0
        win_rates.append({"week": file, "win_rate": win_rate})

    win_rate_df = pd.DataFrame(win_rates)

    # 可視化
    plt.figure(figsize=(10, 5))
    plt.plot(win_rate_df["week"], win_rate_df["win_rate"], marker='o', label="Win Rate")
    plt.xticks(rotation=45)
    plt.xlabel("Week")
    plt.ylabel("Win Rate")
    plt.title("Weekly Win Rate Over Time")
    plt.legend()
    plt.tight_layout()
    plt.show()

    # 例: 利益分布のヒストグラム
    plt.figure(figsize=(8, 4))
    combined_df["profit"].hist(bins=30)
    plt.xlabel("Profit")
    plt.ylabel("Frequency")
    plt.title("Profit Distribution")
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    visualize_trade_history()
