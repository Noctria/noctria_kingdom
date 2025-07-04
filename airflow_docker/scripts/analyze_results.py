#!/usr/bin/env python3
# coding: utf-8

import os
import pandas as pd

def main():
    print("👑 王Noctria: 分析の儀式を開始する。臣下たちよ、準備は整ったか？")

    # 📂 書の場所（将来は引数対応も可）
    file_path = "logs/trade_history_2025-05-31_to_2025-06-07.csv"

    if not os.path.exists(file_path):
        print(f"⚠️ 王Noctria: 書が見つからぬ。{file_path} に探索を命ずる。")
        return

    # 書の開封
    try:
        df = pd.read_csv(file_path)
        print(f"📜 王Noctria: 履歴の書『{file_path}』を開封した。")
    except Exception as e:
        print(f"💥 Levia: 書の読み込みに失敗しました！ 原因: {e}")
        return

    # 欠損補完
    if "drawdown" not in df.columns:
        print("🛡️ Noctus: drawdownカラムは見当たりませぬ。王国の安全を期すため、0で補完いたします。")
        df["drawdown"] = 0

    # 戦果報告
    print("📊 Aurus: 王国の戦果をご報告いたします。")
    print(df.describe())

    # 戦略分析
    win_rate = (df["profit"] >= 0).mean() * 100
    max_drawdown = df["drawdown"].max()

    print(f"🏆 Levia: 勝率は {win_rate:.2f}%。瞬間の勝機をものにしております。")
    print(f"🔻 Noctus: 最大ドローダウンは {max_drawdown}。リスク管理に抜かりはございませぬ。")

    # 書の写しを保存（任意）
    output_path = "logs/analyzed_trade_history.csv"
    df.to_csv(output_path, index=False)
    print(f"🗃️ Prometheus: 分析の書を新たに編纂し、『{output_path}』に保管いたしました。")

    print("✅ 王Noctria: 分析の儀式は滞りなく完了した。次なる戦略の構築に進むとしよう。")

if __name__ == "__main__":
    main()
