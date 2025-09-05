# src/plan_data/run_pdca_plan_workflow.py

import pandas as pd
from datetime import datetime, timedelta
from collector import PlanDataCollector, ASSET_SYMBOLS
from features import FeatureEngineer
from analyzer import PlanAnalyzer

def run_pdca_plan_workflow(lookback_days: int = 90, output_path: str = None):
    collector = PlanDataCollector()
    base_df = collector.collect_all(lookback_days=lookback_days)
    fe = FeatureEngineer(ASSET_SYMBOLS)
    feat_df = fe.add_technical_features(base_df)
    analyzer = PlanAnalyzer(feat_df)
    features = analyzer.extract_features()
    labels = analyzer.make_explanation_labels(features)
    llm_summary = analyzer.generate_llm_summary(features, labels)

    # 保存先が指定されていればサマリーをJSONで保存
    if output_path:
        import json
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "summary": llm_summary,
                "features": features,
                "labels": labels
            }, f, ensure_ascii=False, indent=2)
    return llm_summary

if __name__ == "__main__":
    run_pdca_plan_workflow(lookback_days=90, output_path="data/pdca_plan_summary.json")
