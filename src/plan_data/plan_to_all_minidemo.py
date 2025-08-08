# src/plan_data/plan_to_all_minidemo.py

"""
Plan層→全AIワークフロー最小デモ
- Plan層で標準特徴量DataFrame/dict生成
- Aurus/Levia/Noctus/Prometheus/Hermes/Veritas 全AIへ同一ターン連携・進言を一括取得
"""

import sys
from pathlib import Path
import json
import pandas as pd
import numpy as np

# --- パス調整 ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from plan_data.collector import PlanDataCollector, ASSET_SYMBOLS
from plan_data.features import FeatureEngineer
from plan_data.analyzer import PlanAnalyzer
from strategies.aurus_singularis import AurusSingularis
from strategies.levia_tempest import LeviaTempest
from strategies.noctus_sentinella import NoctusSentinella
from strategies.prometheus_oracle import PrometheusOracle
from strategies.hermes_cognitor import HermesCognitorStrategy
from strategies.veritas_machina import VeritasMachina

def main():
    # 1. 特徴量生成
    collector = PlanDataCollector()
    base_df = collector.collect_all(lookback_days=60)
    fe = FeatureEngineer(ASSET_SYMBOLS)
    feat_df = fe.add_technical_features(base_df)
    # 最新ターンのdict（Aurus/Levia/Noctus等に渡す用）
    feature_dict = feat_df.dropna().iloc[-1].to_dict()
    # 使用カラム順（Aurus/Prometheus/Veritasなど学習型AIで必須）
    feature_order = [c for c in feat_df.columns if c not in {"label", "Date"}]

    print("📝 Plan層標準特徴量セット:", list(feature_dict.keys()))
    print("特徴量（最新ターン）:", feature_dict)

    # 2. Aurus（総合市場分析AI）
    aurus_ai = AurusSingularis(feature_order=feature_order)
    aurus_out = aurus_ai.propose(feature_dict, decision_id="ALLDEMO-001", caller="plan_to_all", reason="一括デモ")
    print("\n🎯 Aurus進言:", aurus_out)

    # 3. Levia（スキャルピングAI）
    levia_ai = LeviaTempest(feature_order=feature_order)
    levia_out = levia_ai.propose(feature_dict, decision_id="ALLDEMO-002", caller="plan_to_all", reason="一括デモ")
    print("\n⚡ Levia進言:", levia_out)

    # 4. Noctus（リスク管理AI, ロット判定あり）
    noctus_ai = NoctusSentinella()
    noctus_out = noctus_ai.calculate_lot_and_risk(
        feature_dict=feature_dict,
        side="BUY",
        entry_price=feature_dict.get("price", 150),
        stop_loss_price=feature_dict.get("price", 150) - 0.3,
        capital=10000,
        risk_percent=0.007,
        decision_id="ALLDEMO-003",
        caller="plan_to_all",
        reason="一括デモ"
    )
    print("\n🛡️ Noctus判定:", noctus_out)

    # 5. Prometheus（未来予測AI）
    prometheus_ai = PrometheusOracle(feature_order=feature_order)
    pred_df = prometheus_ai.predict_future(feat_df, n_days=5, decision_id="ALLDEMO-004", caller="plan_to_all", reason="一括デモ")
    print("\n🔮 Prometheus予測:\n", pred_df.head(5))

    # 6. Hermes（LLM説明AI）
    analyzer = PlanAnalyzer(feat_df)
    explain_features = analyzer.extract_features()
    labels = analyzer.make_explanation_labels(explain_features)
    hermes_ai = HermesCognitorStrategy()
    hermes_out = hermes_ai.propose(
        {"features": explain_features, "labels": labels, "reason": "Plan層全AI連携要約"},
        decision_id="ALLDEMO-005", caller="plan_to_all"
    )
    print("\n🦉 Hermes要約:\n", json.dumps(hermes_out, indent=2, ensure_ascii=False))

    # 7. Veritas（戦略提案AI, symbolは適宜調整）
    veritas_ai = VeritasMachina()
    veritas_out = veritas_ai.propose(
        top_n=2,
        decision_id="ALLDEMO-006",
        caller="plan_to_all",
        lookback=60,
        symbol="USDJPY"
    )
    print("\n🧠 Veritas戦略:\n", json.dumps(veritas_out, indent=2, ensure_ascii=False))

    # --- まとめて保存（例: 全進言をJSONにまとめる） ---
    out = dict(
        aurus=aurus_out,
        levia=levia_out,
        noctus=noctus_out,
        prometheus=pred_df.head(5).to_dict(orient="records"),
        hermes=hermes_out,
        veritas=veritas_out,
    )
    out_path = Path("data/demo/plan_to_all_minidemo.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n📁 進言サマリ保存: {out_path.resolve()}")

if __name__ == "__main__":
    main()
