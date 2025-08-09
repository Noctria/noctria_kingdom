# src/plan_data/standard_feature_schema.py

"""
Plan層：最小必須の標準特徴量の並び
- すべて snake_case
- align_to_feature_spec() と Collector/Features が生成する列名と整合
- plan_to_all_minidemo などで最新行から dict を作る際の順序にも使用
"""

STANDARD_FEATURE_ORDER = [
    # 市場・テクニカル（最小セット）
    "usdjpy_close",
    "usdjpy_volatility_5d",

    # リスク資産／恐怖指数
    "sp500_close",
    "vix_close",

    # ニュース集計
    "news_count",

    # マクロ
    "cpiaucsl_value",
    "fedfunds_value",
    "unrate_value",

    # 必要に応じてこの下に追加（snake_caseで）
    # "dxy_close",
    # "us10y_close",
]
