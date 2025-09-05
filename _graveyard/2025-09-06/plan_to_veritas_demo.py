# src/plan_data/plan_to_veritas_demo.py

import json
from pathlib import Path

from src.core.path_config import DATA_DIR
from src.plan_data.collector import PlanDataCollector, ASSET_SYMBOLS
from src.plan_data.features import FeatureEngineer
from src.strategies.veritas_machina import VeritasMachina

def main():
    # 1. 市場データ収集（直近90日）
    collector = PlanDataCollector()
    print("📥 市場データ収集中...")
    base_df = collector.collect_all(lookback_days=90)
    print(f"収集データ: {base_df.shape}")

    # 2. 特徴量エンジニアリング
    fe = FeatureEngineer(ASSET_SYMBOLS)
    feat_df = fe.add_technical_features(base_df)
    print(f"特徴量付与後: {feat_df.shape}")

    # 3. (Option) 特徴量を一部サンプルで保存
    feat_sample_path = DATA_DIR / "demo" / "plan_features_sample.json"
    feat_sample_path.parent.mkdir(parents=True, exist_ok=True)
    feat_df.tail(10).to_json(feat_sample_path, orient="records", force_ascii=False, indent=2)
    print(f"特徴量サンプル保存: {feat_sample_path}")

    # 4. Veritas戦略AIへデータ連携・提案
    veritas = VeritasMachina()
    res = veritas.propose(
        top_n=3,
        decision_id="DEMO-P2V-001",
        caller="plan_to_veritas_demo",
        lookback=90,
        symbol="USDJPY"
    )
    print("🧠 Veritas Machina 戦略提案結果：")
    print(json.dumps(res, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
