# src/plan_data/plan_to_levia_demo.py

import pandas as pd
from datetime import datetime, timedelta

from plan_data.collector import PlanDataCollector
from plan_data.features import FeatureEngineer
from src.strategies.levia_tempest import LeviaTempest
from plan_data.collector import ASSET_SYMBOLS

def prepare_levia_input(row) -> dict:
    """
    Plan層DataFrameの1行からLevia用dict生成
    """
    return {
        "price": row.get("USDJPY_Close", 0.0),
        "previous_price": row.get("USDJPY_Close", 0.0) - row.get("USDJPY_Return", 0.0) if "USDJPY_Return" in row else row.get("USDJPY_Close", 0.0),
        "volume": row.get("USDJPY_Volume", 0.0),
        "spread": row.get("USDJPY_Spread", 0.015),  # ダミー or 計算値
        "volatility": row.get("USDJPY_Volatility_5d", 0.0),
        "symbol": "USDJPY"
    }

def main(lookback_days: int = 10):
    # 1. データ収集＋特徴量
    collector = PlanDataCollector()
    base_df = collector.collect_all(lookback_days=lookback_days + 1)
    fe = FeatureEngineer(ASSET_SYMBOLS)
    feat_df = fe.add_technical_features(base_df)

    # 必要カラム補完
    if "USDJPY_High" in feat_df.columns and "USDJPY_Low" in feat_df.columns:
        feat_df["USDJPY_Spread"] = feat_df["USDJPY_High"] - feat_df["USDJPY_Low"]
    else:
        feat_df["USDJPY_Spread"] = 0.015

    if "USDJPY_Return" not in feat_df.columns:
        feat_df["USDJPY_Return"] = feat_df["USDJPY_Close"].pct_change()

    levia = LeviaTempest()
    results = []
    for idx, row in feat_df.tail(lookback_days).iterrows():
        market_data = prepare_levia_input(row)
        proposal = levia.propose(market_data, decision_id=f"LEVIA-{idx}", caller="plan_to_levia_demo")
        results.append({
            "date": row.get("Date"),
            "signal": proposal["signal"],
            "confidence": proposal["confidence"],
            "reason": proposal.get("reason", ""),
            "decision_id": proposal["decision_id"]
        })

    df = pd.DataFrame(results)
    print("==== LeviaTempest Demo Results ====")
    print(df)

if __name__ == "__main__":
    main(lookback_days=7)
