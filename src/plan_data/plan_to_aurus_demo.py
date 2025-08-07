# plan_to_aurus_demo.py
"""
Noctria Kingdom - Plan標準特徴量 → 臣下AI進言デモ
- Plan層で生成された特徴量DataFrameの「直近行」をAurus/Levia/Noctusに投げるパイプライン
"""

import pandas as pd
from src.plan_data.collector import PlanDataCollector, ASSET_SYMBOLS
from src.plan_data.features import FeatureEngineer
from src.strategies.aurus_singularis import AurusSingularis
from src.strategies.levia_tempest import LeviaTempest
from src.strategies.noctus_sentinella import NoctusSentinella

def main():
    # --- 1. Plan層で特徴量DataFrameを生成 ---
    print("🛠️ Plan層: 特徴量生成")
    collector = PlanDataCollector()
    base_df = collector.collect_all(lookback_days=90)
    fe = FeatureEngineer(ASSET_SYMBOLS)
    feat_df = fe.add_technical_features(base_df)

    # --- 2. 最新（直近）1行分のdictを用意 ---
    if len(feat_df) == 0:
        print("❌ データフレームが空です。")
        return
    latest_feature_dict = feat_df.iloc[-1].to_dict()
    print("📝 最新特徴量サンプル:")
    for k, v in list(latest_feature_dict.items())[:12]:
        print(f"  {k}: {v}")
    decision_id = "KC-DEMO-20250807"
    caller = "plan_to_aurus_demo.py"

    # --- 3. Aurus (市場分析AI) 進言 ---
    print("\n🧠 Aurus Singularis 進言:")
    aurus = AurusSingularis()
    aurus_report = aurus.propose(latest_feature_dict, decision_id=decision_id, caller=caller)
    print(aurus_report)

    # --- 4. Levia (スキャルピングAI) 進言 ---
    print("\n⚡ Levia Tempest 進言:")
    levia = LeviaTempest()
    levia_report = levia.propose(latest_feature_dict, decision_id=decision_id, caller=caller)
    print(levia_report)

    # --- 5. Noctus (リスクAI) 進言 ---
    print("\n🛡️ Noctus Sentinella 進言:")
    # Noctusはhistorical_dataが必要→最低限USDJPY_CloseでDataFrame生成
    # ※ここは必要に応じて本物の時系列DataFrameを渡す
    if "USDJPY_Close" in base_df.columns:
        historical_df = base_df[["Date", "USDJPY_Close"]].tail(100).copy()
    else:
        historical_df = pd.DataFrame()
    latest_feature_dict['historical_data'] = historical_df
    noctus = NoctusSentinella()
    noctus_report = noctus.assess(
        latest_feature_dict,
        proposed_action=aurus_report.get("signal", "HOLD"),
        decision_id=decision_id,
        caller=caller,
        reason="Aurusの進言に対するリスク評価"
    )
    print(noctus_report)

if __name__ == "__main__":
    main()
