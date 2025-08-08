# src/plan_data/plan_to_prometheus_demo.py

"""
Plan層（collector→features→statistics）からPrometheus Oracleへの連携デモ
- 市場特徴量DFから未来予測を生成し、可視化・指標を出力
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys
from pathlib import Path

# --- モジュールimport ---
sys.path.append(str(Path(__file__).resolve().parent.parent))  # src/plan_data/へのパス調整

from collector import PlanDataCollector, ASSET_SYMBOLS
from features import FeatureEngineer
from statistics import PlanStatistics

# Prometheus Oracle本体
sys.path.append(str(Path(__file__).resolve().parent.parent.parent / "strategies"))
from prometheus_oracle import PrometheusOracle

def main():
    # --- ① 市場データ・特徴量生成 ---
    collector = PlanDataCollector()
    base_df = collector.collect_all(lookback_days=120)
    fe = FeatureEngineer(ASSET_SYMBOLS)
    feat_df = fe.add_technical_features(base_df)
    print("📝 Plan層の特徴量DF（最新5行）:")
    print(feat_df.tail(5))

    # --- ② Prometheus Oracleで未来予測 ---
    oracle = PrometheusOracle()
    n_days = 14
    forecast_df = oracle.predict_with_confidence(n_days=n_days, output="df", decision_id="DEMO-001", caller="plan_to_prometheus_demo")
    print(f"\n🔮 Prometheusによる未来予測({n_days}日):")
    print(forecast_df.head())

    # --- ③ テスト用指標出力 ---
    metrics = oracle.get_metrics()
    print("\n📊 予測モデル評価指標:")
    for k, v in metrics.items():
        print(f"{k}: {v}")

    # --- ④ 予測結果をJSON出力（オプション） ---
    json_path = Path("data/prometheus_forecast_demo.json")
    forecast_df.to_json(json_path, orient="records", force_ascii=False, indent=2)
    print(f"\n📁 予測結果JSON: {json_path.resolve()}")

if __name__ == "__main__":
    main()
