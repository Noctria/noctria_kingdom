# src/plan_data/plan_to_levia_demo.py

import pandas as pd
from datetime import datetime, timedelta

from src.plan_data.collector import PlanDataCollector
from src.plan_data.features import FeatureEngineer
from src.strategies.levia_tempest import LeviaTempest
from src.plan_data.collector import ASSET_SYMBOLS

def prepare_levia_input(row) -> dict:
    """
    Plan層の特徴量DataFrameの1行からLeviaTempest用dictに変換
    """
    # USDJPY関連・volume/volatility/スプレッドだけで良いが、柔軟に拡張
    return {
        "price": row.get("USDJPY_Close", 0.0),
        "previous_price": row.get("USDJPY_Close_prev", 0.0),  # 新たに生成する
        "volume": row.get("USDJPY_Volume", 0.0),
        "volatility": row.get("USDJPY_Volatility_5d", 0.0),
        "spread": row.get("USDJPY_Spread", 0.015),  # スプレッド計算値がある場合のみ
        "symbol": "USDJPY"
    }

def main(lookback_days: int = 10):
    # 1. データ収集と特徴量エンジニアリング
    collector = PlanDataCollector()
    base_df = collector.collect_all(lookback_days=lookback_days)
    fe = FeatureEngineer(ASSET_SYMBOLS)
    feat_df = fe.add_technical_features(base_df)

    # スプレッドやprevious_priceを補う（デモ用簡易計算）
    if "USDJPY_Close" in feat_df.columns:
        feat_df["USDJPY_Close_prev"] = feat_df["USDJPY_Close"].shift(1)
    if "USDJPY_High" in feat_df.columns and "USDJPY_Low" in feat_df.columns:
        feat_df["USDJPY_Spread"] = feat_df["USDJPY_High"] - feat_df["USDJPY_Low"]
    else:
        feat_df["USDJPY_Spread"] = 0.015  # ダミー値

    levia = LeviaTempest()
    results = []
    for idx, row in feat_df.tail(lookback_days).iterrows():
        market_data = prepare_levia_input(row)
        proposal = levia.propose(market_data, decision_id=f"LEVIA-{idx}", caller="plan_to_levia_demo")
        results.append({
            "date": row.get("Date"),
            "signal": proposal["signal"],
            "confidence": proposal["confidence"],
            "price": market_data["price"],
            "volatility": market_data["volatility"],
            "volume": market_data["volume"],
            "spread": market_data["spread"],
            "decision_id": proposal["decision_id"]
        })

    df = pd.DataFrame(results)
    print("==== LeviaTempest Demo Results ====")
    print(df)

if __name__ == "__main__":
    main(lookback_days=10)
