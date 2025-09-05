# test_plan_analyzer.py

import pandas as pd
from plan_data.analyzer import PlanAnalyzer

# サンプルダミーデータ作成
data = {
    "date": pd.date_range("2024-07-01", periods=14),
    "win_rate": [70, 72, 69, 71, 73, 76, 78, 82, 85, 82, 81, 80, 83, 87],
    "max_dd":  [-6, -5, -8, -7, -4, -3, -2, -2, -1, -2, -2, -1, -2, -2],
    "num_trades": [42, 40, 38, 45, 48, 50, 51, 53, 54, 55, 57, 58, 60, 61],
    "strategy": ["S1", "S1", "S2", "S2", "S2", "S1", "S1", "S2", "S2", "S2", "S1", "S1", "S2", "S2"],
    "News_Count": [8, 7, 6, 10, 12, 11, 20, 24, 27, 22, 23, 22, 21, 19],
    "News_Positive": [5, 3, 3, 4, 6, 7, 9, 14, 14, 13, 12, 10, 10, 11],
    "News_Negative": [2, 3, 2, 5, 4, 2, 3, 5, 7, 7, 5, 5, 4, 3],
    "CPI_Value": [2.1, 2.2, 2.0, 1.9, 2.4, 2.8, 3.2, 3.4, 3.6, 3.3, 3.1, 3.0, 3.2, 3.1],
    "FOMC":      [0]*13 + [1],  # 最後の日だけFOMCイベント日
}
stats_df = pd.DataFrame(data)

# インスタンス生成
analyzer = PlanAnalyzer(stats_df=stats_df)

# 特徴量抽出
features = analyzer.extract_features()
print("=== 抽出された特徴量 ===")
for k, v in features.items():
    print(f"{k}: {v}")

# ラベル生成
labels = analyzer.make_explanation_labels(features)
print("\n=== 説明ラベル（自動生成） ===")
for label in labels:
    print(label)

# タグ別トレンド（タグ情報なしダミーなので今回はスキップ）

# LLMサマリー（現状ダミー返し）
llm_summary = analyzer.generate_llm_summary(features, labels)
print("\n=== LLMサマリー（ダミー） ===")
print(llm_summary)
