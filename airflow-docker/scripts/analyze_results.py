#!/usr/bin/env python3
# coding: utf-8

import pandas as pd

def main():
    print("👑 王Noctria: 分析の儀式を開始する。臣下たちよ、準備は整ったか？")

    # トレード履歴の書を開く
    file_path = "logs/trade_history_2025-05-31_to_2025-06-07.csv"
    try:
        df = pd.read_csv(file_path)
        print(f"📜 王Noctria: 履歴の書『{file_path}』を開封した。")
    except FileNotFoundError:
        print(f"⚠️ 王Noctria: 書が見つからぬ。{file_path} に探索を命ずる。")
        return

    # drawdown カラムの有無を確認
    if "drawdown" not in df.columns:
        print("🛡️ Noctus: drawdownカラムは見当たりませぬ。王国の安全を期すため、0で補完いたします。")
        df["drawdown"] = 0

    # 王国の戦果を報告
    print("📊 Aurus: 王国の戦果をお見せいたします。")
    print(df.describe())

    # 戦果の詳細を吟味
    win_rate = (df["profit"] >= 0).mean() * 100
    max_drawdown = df["drawdown"].max()

    print(f"🏆 Levia: 勝率は {win_rate:.2f}%。瞬間の勝機をものにしております。")
    print(f"🔻 Noctus: 最大ドローダウンは {max_drawdown}。リスク管理に抜かりはございませぬ。")

    # 必要なら更に深い戦略書を編纂
    # 例: df.to_csv("logs/analyzed_trade_history.csv", index=False)

    print("✅ 王Noctria: 分析の儀式は滞りなく完了した。次なる戦略の構築に進むとしよう。")

if __name__ == "__main__":
    main()
