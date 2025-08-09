# src/plan_data/plan_to_all_minidemo.py

import json
import pandas as pd
import numpy as np

from src.core.path_config import DATA_DIR
from src.plan_data.collector import PlanDataCollector, ASSET_SYMBOLS
from src.plan_data.features import FeatureEngineer
from src.plan_data.analyzer import PlanAnalyzer
from src.plan_data.standard_feature_schema import STANDARD_FEATURE_ORDER

from src.strategies.aurus_singularis import AurusSingularis
from src.strategies.levia_tempest import LeviaTempest
from src.strategies.noctus_sentinella import NoctusSentinella
from src.strategies.prometheus_oracle import PrometheusOracle
from src.strategies.hermes_cognitor import HermesCognitorStrategy
from src.veritas.veritas_machina import VeritasMachina


def main():
    # 1. 特徴量生成
    collector = PlanDataCollector()
    base_df = collector.collect_all(lookback_days=60)
    fe = FeatureEngineer(ASSET_SYMBOLS)
    feat_df = fe.add_technical_features(base_df)

    print("=== feat_df columns ===")
    print(feat_df.columns.tolist())

    # ---------- ここから堅牢化ブロック ----------
    # STANDARD_FEATURE_ORDER と実データの交差のみを対象
    available_cols = [c for c in STANDARD_FEATURE_ORDER if c in feat_df.columns]

    # 前方埋めで営業日/公表日ギャップを緩和（存在する列のみ）
    if available_cols:
        feat_df[available_cols] = feat_df[available_cols].ffill()

    # コア必須列（段階的に緩和）
    core_candidates = ["usdjpy_close", "sp500_close", "vix_close"]
    core_subset = [c for c in core_candidates if c in available_cols]

    if core_subset:
        valid_df = feat_df.dropna(subset=core_subset, how="any")
    else:
        # 最低限 USDJPY がなければ実行不可
        if "usdjpy_close" in feat_df.columns:
            valid_df = feat_df.dropna(subset=["usdjpy_close"], how="any")
        else:
            raise RuntimeError(
                "必要なコア列が存在しません（usdjpy_close も見つかりませんでした）。"
            )

    # それでも空ならフォールバックして最終行を使う
    if valid_df.empty:
        valid_df = feat_df.copy()

    latest_row = valid_df.iloc[-1]

    # 出力順は「存在する列」のみ
    feature_order = available_cols if available_cols else [c for c in STANDARD_FEATURE_ORDER if c in valid_df.columns]

    # 値は存在しない列は 0.0 で埋める（必要に応じて np.nan に変更可）
    feature_dict = {
        col: (latest_row[col] if col in valid_df.columns else 0.0)
        for col in feature_order
    }
    # ---------- ここまで堅牢化ブロック ----------

    print("📝 Plan層標準特徴量セット:", feature_order)
    print("特徴量（最新ターン）:", feature_dict)

    # 2. Aurus
    aurus_ai = AurusSingularis(feature_order=feature_order)
    aurus_out = aurus_ai.propose(
        feature_dict,
        decision_id="ALLDEMO-001",
        caller="plan_to_all",
        reason="一括デモ",
    )
    print("\n🎯 Aurus進言:", aurus_out)

    # 3. Levia
    levia_ai = LeviaTempest(feature_order=feature_order)
    levia_out = levia_ai.propose(
        feature_dict,
        decision_id="ALLDEMO-002",
        caller="plan_to_all",
        reason="一括デモ",
    )
    print("\n⚡ Levia進言:", levia_out)

    # 4. Noctus
    noctus_ai = NoctusSentinella()
    noctus_out = noctus_ai.calculate_lot_and_risk(
        feature_dict=feature_dict,
        side="BUY",
        entry_price=feature_dict.get("usdjpy_close", 150),
        stop_loss_price=feature_dict.get("usdjpy_close", 150) - 0.3,
        capital=10000,
        risk_percent=0.007,
        decision_id="ALLDEMO-003",
        caller="plan_to_all",
        reason="一括デモ",
    )
    print("\n🛡️ Noctus判定:", noctus_out)

    # 5. Prometheus
    prometheus_ai = PrometheusOracle(feature_order=feature_order)
    pred_df = prometheus_ai.predict_future(
        valid_df, n_days=5, decision_id="ALLDEMO-004", caller="plan_to_all", reason="一括デモ"
    )
    print("\n🔮 Prometheus予測:\n", pred_df.head(5))

    # 6. Hermes
    analyzer = PlanAnalyzer(valid_df)
    explain_features = analyzer.extract_features()
    labels = analyzer.make_explanation_labels(explain_features)
    hermes_ai = HermesCognitorStrategy()
    hermes_out = hermes_ai.propose(
        {"features": explain_features, "labels": labels, "reason": "Plan層全AI連携要約"},
        decision_id="ALLDEMO-005",
        caller="plan_to_all",
    )
    print("\n🦉 Hermes要約:\n", json.dumps(hermes_out, indent=2, ensure_ascii=False))

    # 7. Veritas
    veritas_ai = VeritasMachina()
    veritas_out = veritas_ai.propose(
        top_n=2,
        decision_id="ALLDEMO-006",
        caller="plan_to_all",
        lookback=60,
        symbol="USDJPY",
    )
    print("\n🧠 Veritas戦略:\n", json.dumps(veritas_out, indent=2, ensure_ascii=False))

    # --- まとめて保存 ---
    out = dict(
        aurus=aurus_out,
        levia=levia_out,
        noctus=noctus_out,
        prometheus=pred_df.head(5).to_dict(orient="records"),
        hermes=hermes_out,
        veritas=veritas_out,
    )
    out_path = DATA_DIR / "demo" / "plan_to_all_minidemo.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n📁 進言サマリ保存: {out_path.resolve()}")


if __name__ == "__main__":
    main()
