# src/plan_data/plan_to_hermes_demo.py

import json
from pathlib import Path

from src.core.path_config import DATA_DIR
from src.plan_data.collector import PlanDataCollector, ASSET_SYMBOLS
from src.plan_data.features import FeatureEngineer
from src.plan_data.analyzer import PlanAnalyzer
from src.strategies.hermes_cognitor import HermesCognitorStrategy

def main():
    # 1. 特徴量・要因ラベルをPlan層から生成
    collector = PlanDataCollector()
    base_df = collector.collect_all(lookback_days=90)
    fe = FeatureEngineer(ASSET_SYMBOLS)
    feat_df = fe.add_technical_features(base_df)
    analyzer = PlanAnalyzer(feat_df)
    features = analyzer.extract_features()
    labels = analyzer.make_explanation_labels(features)

    # 2. Hermes Cognitorで説明生成
    hermes = HermesCognitorStrategy(model="gpt-4o")
    print("🦉 Hermes Cognitorに説明生成を依頼中…")
    reason = "未来予測計画の要約デモ"
    decision_id = "DEMO-HERMES-001"
    proposal = hermes.propose(
        {
            "features": features,
            "labels": labels,
            "reason": reason
        },
        decision_id=decision_id,
        caller="plan_to_hermes_demo"
    )

    # 3. 結果表示＆保存
    print(json.dumps(proposal, indent=2, ensure_ascii=False))
    out_path = DATA_DIR / "demo" / "hermes_summary_sample.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(proposal, f, ensure_ascii=False, indent=2)
    print(f"説明要約結果を保存: {out_path}")

if __name__ == "__main__":
    main()
