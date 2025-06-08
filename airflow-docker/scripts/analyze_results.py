#!/usr/bin/env python3
# coding: utf-8

import pandas as pd

def analyze_trades(log_csv):
    print("👑 王Noctria: Aurus、Noctus、Levia、Prometheusよ、本日の戦略成果を報告せよ！")

    df = pd.read_csv(log_csv)
    total_trades = len(df)
    total_profit = df['profit'].sum()
    win_rate = (df['profit'] > 0).mean() * 100
    max_drawdown = df['drawdown'].max()

    print("⚔️ Aurus: 勝率は {:.2f}%。全体取引数は {} 件。".format(win_rate, total_trades))
    print("⚡ Levia: 短期戦での総利益は {:.2f}。".format(total_profit))
    print("🛡️ Noctus: 最大ドローダウンは {:.2f}。リスク管理に注視します。".format(max_drawdown))
    print("🔮 Prometheus: 外部環境に基づく未来の戦略調整を検討します。")
    print("✅ 王Noctria: 本日の戦略成果報告を受理した。次の成長へ備えよ！")

if __name__ == "__main__":
    # 例: ログCSVファイル名
    log_csv = "/opt/airflow/logs/trade_history_2025-05-31_to_2025-06-07.csv"
    analyze_trades(log_csv)
