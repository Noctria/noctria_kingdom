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


def _safe_float(x, default=0.0):
    try:
        if pd.isna(x):
            return float(default)
        return float(x)
    except Exception:
        return float(default)


def main():
    # 1) 収集 → 特徴量化
    collector = PlanDataCollector()
    base_df = collector.collect_all(lookback_days=60)
    fe = FeatureEngineer(ASSET_SYMBOLS)
    feat_df = fe.add_technical_features(base_df)

    print("=== feat_df columns ===")
    print(feat_df.columns.tolist())

    # ---------- データ堅牢化（末尾NaN対策） ----------
    feat_df = feat_df.sort_values("date")

    # 月次マクロは前方→後方で埋める（末尾NaNつぶし）
    for col in ["cpiaucsl_value", "unrate_value", "fedfunds_value"]:
        if col in feat_df.columns:
            feat_df[col] = pd.to_numeric(feat_df[col], errors="coerce").ffill().bfill()

    # NewsAPI 未設定時は NaN になりやすいので 0 埋め
    news_cols = [
        "news_count", "news_positive", "news_negative",
        "news_positive_ratio", "news_negative_ratio",
        "news_spike_flag", "news_count_change",
        "news_positive_lead", "news_negative_lead",
    ]
    for col in news_cols:
        if col in feat_df.columns:
            feat_df[col] = pd.to_numeric(feat_df[col], errors="coerce").fillna(0.0)

    # 標準特徴量のうち存在する列のみを対象に前方埋め
    available_cols = [c for c in STANDARD_FEATURE_ORDER if c in feat_df.columns]
    if available_cols:
        feat_df[available_cols] = feat_df[available_cols].ffill()

    # コア（USDJPY/先物指数/ボラ）で最小限の行を確保
    core_candidates = ["usdjpy_close", "sp500_close", "vix_close"]
    core_subset = [c for c in core_candidates if c in available_cols]

    if core_subset:
        valid_df = feat_df.dropna(subset=core_subset, how="any")
    else:
        if "usdjpy_close" in feat_df.columns:
            valid_df = feat_df.dropna(subset=["usdjpy_close"], how="any")
        else:
            raise RuntimeError("必要なコア列が存在しません（usdjpy_close が見つかりません）。")

    # それでも空なら全体から最終行を使う
    if valid_df.empty:
        valid_df = feat_df.copy()

    latest_row = valid_df.iloc[-1]

    # 実在する列のみを order にする（順序は STANDARD_FEATURE_ORDER 準拠）
    feature_order = available_cols if available_cols else [c for c in STANDARD_FEATURE_ORDER if c in valid_df.columns]

    # 値が NaN ならその列の直近値で補完、無ければ 0.0
    feature_dict = {}
    for col in feature_order:
        if col in valid_df.columns:
            val = latest_row[col]
            if pd.isna(val):
                non_na = valid_df[col].dropna()
                feature_dict[col] = _safe_float(non_na.iloc[-1] if not non_na.empty else 0.0)
            else:
                feature_dict[col] = _safe_float(val)
        else:
            feature_dict[col] = 0.0
    # ---------- ここまで堅牢化 ----------

    print("📝 Plan層標準特徴量セット:", feature_order)
    print("特徴量（最新ターン）:", feature_dict)

    # 2) Aurus
    aurus_ai = AurusSingularis(feature_order=feature_order)
    aurus_out = aurus_ai.propose(
        feature_dict,
        decision_id="ALLDEMO-001",
        caller="plan_to_all",
        reason="一括デモ",
    )
    print("\n🎯 Aurus進言:", aurus_out)

    # 3) Levia
    levia_ai = LeviaTempest(feature_order=feature_order)
    levia_out = levia_ai.propose(
        feature_dict,
        decision_id="ALLDEMO-002",
        caller="plan_to_all",
        reason="一括デモ",
    )
    print("\n⚡ Levia進言:", levia_out)

    # 4) Noctus
    noctus_ai = NoctusSentinella()
    noctus_out = noctus_ai.calculate_lot_and_risk(
        feature_dict=feature_dict,
        side="BUY",
        entry_price=feature_dict.get("usdjpy_close", 150.0),
        stop_loss_price=feature_dict.get("usdjpy_close", 150.0) - 0.3,
        capital=10000,
        risk_percent=0.007,
        decision_id="ALLDEMO-003",
        caller="plan_to_all",
        reason="一括デモ",
    )
    print("\n🛡️ Noctus判定:", noctus_out)

    # 5) Prometheus（入力NaNは内部でも落とすが念のため valid_df を渡す）
    prometheus_ai = PrometheusOracle(feature_order=feature_order)
    pred_df = prometheus_ai.predict_future(
        valid_df, n_days=5, decision_id="ALLDEMO-004", caller="plan_to_all", reason="一括デモ"
    )
    print("\n🔮 Prometheus予測:\n", pred_df.head(5))

    # 6) Hermes
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

    # 7) Veritas（別プロセス/別モジュールの import 経路は別途修正推奨）
    veritas_ai = VeritasMachina()
    veritas_out = veritas_ai.propose(
        top_n=2,
        decision_id="ALLDEMO-006",
        caller="plan_to_all",
        lookback=60,
        symbol="USDJPY",
    )
    print("\n🧠 Veritas戦略:\n", json.dumps(veritas_out, indent=2, ensure_ascii=False))

    # --- 保存 ---
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
