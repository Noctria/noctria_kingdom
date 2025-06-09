import pandas as pd
import json

# CSVファイル読み込み
trade_history_file = "logs/trade_history_2025-05-31_to_2025-06-07.csv"
df = pd.read_csv(trade_history_file)

print("🔍 トレード履歴サマリー")
print(df.describe())
print("カラム一覧:", df.columns.tolist())

# drawdownカラムが無い場合の確認
if "drawdown" not in df.columns:
    print("⚠️ drawdownカラムが存在しません。")

# JSONファイル読み込み
best_params_file = "best_params.json"
with open(best_params_file, "r") as f:
    best_params = json.load(f)
print("🔍 最適化パラメータ:", best_params)
