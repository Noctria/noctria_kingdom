# src/plan_data/plan_to_noctus_demo.py

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.plan_data.collector import PlanDataCollector
from src.plan_data.features import FeatureEngineer
from src.strategies.noctus_sentinella import NoctusSentinella
from src.plan_data.collector import ASSET_SYMBOLS

def prepare_noctus_input(row, hist_df) -> dict:
    """
    Plan層の特徴量DataFrameの1行＋ヒストリカルDataFrameからNoctus用dict生成
    """
    # Noctusはvolume, volatility, spread, price, historical_data必須
    return {
        "price": row.get("USDJPY_Close", 0.0),
        "volume": row.get("USDJPY_Volume", 0.0),
        "spread": row.get("USDJPY_Spread", 0.015),  # ダミー or 計算値
        "volatility": row.get("USDJPY_Volatility_5d", 0.0),
        "historical_data": hist_df[["USDJPY_Close"]].copy().rename(columns={"USDJPY_Close": "Close"}),
        "symbol": "USDJPY"
    }

def main(lookback_days: int = 10):
    # 1. データ収集＋特徴量
    collector = PlanDataCollector()
    base_df = collector.collect_all(lookback_days=lookback_days + 100)  # ヒストリカル十分に
    fe = FeatureEngineer(ASSET_SYMBOLS)
    feat_df = fe.add_technical_features(base_df)

    # 必要カラム補完
    if "USDJPY_High" in feat_df.columns and "USDJPY_Low" in feat_df.columns:
        feat_df["USDJPY_Spread"] = feat_df["USDJPY_High"] - feat_df["USDJPY_Low"]
    else:
        feat_df["USDJPY_Spread"] = 0.015

    noctus = NoctusSentinella()
    results = []
    for idx, row in feat_df.tail(lookback_days).iterrows():
        # 各行より直近100日をhistorical_dataとして渡す
        hist_df = feat_df.loc[:idx].tail(100).reset_index(drop=True)
        market_data = prepare_noctus_input(row, hist_df)
        # 仮のアクション：BUY, SELL, HOLDで評価
        for action in ["BUY", "SELL", "HOLD"]:
            assessment = noctus.assess(market_data, proposed_action=action, decision_id=f"NOCTUS-{idx}-{action}", caller="plan_to_noctus_demo")
            results.append({
                "date": row.get("Date"),
                "action": action,
                "decision": assessment["decision"],
                "risk_score": assessment["risk_score"],
                "reason": assessment["reason"],
                "decision_id": assessment["decision_id"]
            })

    df = pd.DataFrame(results)
    print("==== NoctusSentinella Demo Results ====")
    print(df)

if __name__ == "__main__":
    main(lookback_days=7)
