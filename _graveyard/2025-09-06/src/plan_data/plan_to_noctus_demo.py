# src/plan_data/plan_to_noctus_demo.py

import pandas as pd
from datetime import datetime, timedelta

from plan_data.collector import PlanDataCollector
from plan_data.features import FeatureEngineer
from src.strategies.noctus_sentinella import NoctusSentinella
from plan_data.collector import ASSET_SYMBOLS

def prepare_noctus_input(row, hist_df) -> dict:
    """
    Plan層DataFrameの1行＋ヒストリカルからNoctus用dict生成
    """
    return {
        "price": row.get("USDJPY_Close", 0.0),
        "volume": row.get("USDJPY_Volume", 0.0),
        "spread": row.get("USDJPY_Spread", 0.015),
        "volatility": row.get("USDJPY_Volatility_5d", 0.0),
        "historical_data": hist_df[["USDJPY_Close"]].rename(columns={"USDJPY_Close": "Close"}).tail(100).reset_index(drop=True) if "USDJPY_Close" in hist_df else pd.DataFrame(),
        "symbol": "USDJPY"
    }

def main(lookback_days: int = 10):
    # 1. データ収集＋特徴量
    collector = PlanDataCollector()
    base_df = collector.collect_all(lookback_days=lookback_days + 100)
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
        # 直近100件のUSDJPY_Closeをhistoryとして渡す
        market_data = prepare_noctus_input(row, feat_df.iloc[:idx+1])
        # 仮シグナル：BUY/HOLD/SELLをローテで与える
        if idx % 3 == 0:
            action = "BUY"
        elif idx % 3 == 1:
            action = "SELL"
        else:
            action = "HOLD"
        assessment = noctus.assess(market_data, proposed_action=action, decision_id=f"NOCTUS-{idx}", caller="plan_to_noctus_demo")
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
