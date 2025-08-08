# src/plan_data/feature_spec.py

"""
Noctria Kingdom - Plan層 標準特徴量セット・サンプルDataFrame
-------------------------------------------------------------
- Plan（計画・戦略立案）フェーズで生成・出力される標準データセット
- src/plan_data/以下のcollector/statistics/features/analyzer等から出力され、
  各AI臣下（Aurus/Levia/Noctus/Prometheus etc）が共通的に受け取る
- カラムや内容を拡張した場合は必ずここを“公式仕様”として更新する
"""

import pandas as pd

# --- Plan層標準カラムセット ---
PLAN_FEATURE_COLUMNS = [
    "date", "tag", "strategy",
    "usdjpy_close", "usdjpy_volume", "usdjpy_return",
    "usdjpy_volatility_5d", "usdjpy_volatility_20d", "usdjpy_rsi_14d",
    "usdjpy_gc_flag", "usdjpy_po_up", "usdjpy_po_down",
    "news_count", "news_positive", "news_negative",
    "news_positive_ratio", "news_negative_ratio", "news_spike_flag",
    "cpiaucsl_value", "cpiaucsl_diff", "cpiaucsl_spike_flag",
    "fedfunds_value", "fedfunds_diff", "fedfunds_spike_flag",
    "fomc", "nfp",
    "win_rate", "max_dd", "num_trades"
]

# --- サンプルDataFrame（実際にAI臣下が受け取る形式例） ---
SAMPLE_PLAN_DF = pd.DataFrame([
    {
        "Date": "2025-08-01", "tag": "bull_trend", "strategy": "v2-ma-cross",
        "USDJPY_Close": 155.23, "USDJPY_Volume": 4000, "USDJPY_Return": 0.002,
        "USDJPY_Volatility_5d": 0.007, "USDJPY_Volatility_20d": 0.009, "USDJPY_RSI_14d": 72.4,
        "USDJPY_GC_Flag": 1, "USDJPY_PO_UP": 1, "USDJPY_PO_DOWN": 0,
        "News_Count": 21, "News_Positive": 9, "News_Negative": 6,
        "News_Positive_Ratio": 0.428, "News_Negative_Ratio": 0.286, "News_Spike_Flag": 0,
        "CPIAUCSL_Value": 310.12, "CPIAUCSL_Diff": 0.13, "CPIAUCSL_Spike_Flag": 0,
        "FEDFUNDS_Value": 5.25, "FEDFUNDS_Diff": 0.00, "FEDFUNDS_Spike_Flag": 0,
        "FOMC": 1, "NFP": 0,
        "win_rate": 0.81, "max_dd": -7.4, "num_trades": 32
    },
    {
        "Date": "2025-08-02", "tag": "range", "strategy": "v2-ma-cross",
        "USDJPY_Close": 154.88, "USDJPY_Volume": 3100, "USDJPY_Return": -0.0023,
        "USDJPY_Volatility_5d": 0.008, "USDJPY_Volatility_20d": 0.010, "USDJPY_RSI_14d": 60.5,
        "USDJPY_GC_Flag": 0, "USDJPY_PO_UP": 0, "USDJPY_PO_DOWN": 0,
        "News_Count": 16, "News_Positive": 3, "News_Negative": 7,
        "News_Positive_Ratio": 0.188, "News_Negative_Ratio": 0.438, "News_Spike_Flag": 0,
        "CPIAUCSL_Value": 310.13, "CPIAUCSL_Diff": 0.01, "CPIAUCSL_Spike_Flag": 0,
        "FEDFUNDS_Value": 5.25, "FEDFUNDS_Diff": 0.00, "FEDFUNDS_Spike_Flag": 0,
        "FOMC": 0, "NFP": 1,
        "win_rate": 0.75, "max_dd": -8.9, "num_trades": 28
    },
    {
        "Date": "2025-08-03", "tag": "bear_trend", "strategy": "v2-ma-cross",
        "USDJPY_Close": 154.56, "USDJPY_Volume": 3800, "USDJPY_Return": -0.0021,
        "USDJPY_Volatility_5d": 0.010, "USDJPY_Volatility_20d": 0.011, "USDJPY_RSI_14d": 53.1,
        "USDJPY_GC_Flag": 0, "USDJPY_PO_UP": 0, "USDJPY_PO_DOWN": 1,
        "News_Count": 20, "News_Positive": 4, "News_Negative": 11,
        "News_Positive_Ratio": 0.20, "News_Negative_Ratio": 0.55, "News_Spike_Flag": 1,
        "CPIAUCSL_Value": 310.15, "CPIAUCSL_Diff": 0.02, "CPIAUCSL_Spike_Flag": 0,
        "FEDFUNDS_Value": 5.25, "FEDFUNDS_Diff": 0.00, "FEDFUNDS_Spike_Flag": 0,
        "FOMC": 0, "NFP": 0,
        "win_rate": 0.68, "max_dd": -12.0, "num_trades": 27
    }
    # ...必要に応じ追加
])

# --- ドキュメント出力例 ---
if __name__ == "__main__":
    print("■ Plan層 標準特徴量セット")
    print(PLAN_FEATURE_COLUMNS)
    print("\n■ サンプルDataFrame（冒頭3行）")
    print(SAMPLE_PLAN_DF.head(3))

FEATURE_SPEC = PLAN_FEATURE_COLUMNS
