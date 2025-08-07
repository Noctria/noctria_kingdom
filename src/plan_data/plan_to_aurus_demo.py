# src/plan_data/plan_to_aurus_demo.py

"""
Noctria Kingdomデータフロー検証:
Plan層の特徴量DataFrame→AurusSingularis AI入力→予測シグナル出力デモ

- 標準特徴量セットを自動生成
- AurusSingularisが期待する形式のdictへ変換
- AIへバッチ/逐次で予測を投げて結果を表示

実行例:
    $ python src/plan_data/plan_to_aurus_demo.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

# --- 必要なモジュールimport ---
sys.path.append(str(Path(__file__).resolve().parent))
from features import FeatureEngineer
from collector import PlanDataCollector, ASSET_SYMBOLS

# --- Aurus AI本体import ---
sys.path.append(str(Path(__file__).parents[1] / "strategies"))
from aurus_singularis import AurusSingularis

# ---------- 1. Plan層データ生成 ----------
def generate_plan_features(n_days=15):
    """
    Plan層での特徴量DataFrameサンプルを生成
    """
    # 市場データ収集
    collector = PlanDataCollector()
    base_df = collector.collect_all(lookback_days=n_days + 20)  # 多少余裕を持つ

    # テクニカル特徴量付与
    fe = FeatureEngineer(ASSET_SYMBOLS)
    feat_df = fe.add_technical_features(base_df)

    # 末尾n件だけ切り出し（Aurusデモ用）
    feat_df = feat_df.tail(n_days).reset_index(drop=True)
    return feat_df

# ---------- 2. DataFrame → AI向けdictへ変換 ----------
def plan_row_to_aurus_dict(row: pd.Series) -> dict:
    """
    Plan層特徴量DFの1行からAurusSingularisが必要とする特徴量dictへ変換
    """
    return {
        # 必須入力（Aurus現行仕様に揃える）
        "price": float(row.get("USDJPY_Close", np.nan)),
        "previous_price": float(row.get("USDJPY_Close", np.nan)),  # ここは連続データでshift可
        "volume": float(row.get("USDJPY_Volume", np.nan)),
        "volatility": float(row.get("USDJPY_Volatility_5d", np.nan)),
        "sma_5_vs_20_diff": float(
            row.get("USDJPY_MA5", np.nan) - row.get("USDJPY_MA25", np.nan)
        ),
        "macd_signal_diff": float(row.get("USDJPY_Return", np.nan)),  # 仮置き
        "trend_strength": 0.5,  # 追加実装可
        "trend_prediction": "neutral",  # 追加実装可
        "rsi_14": float(row.get("USDJPY_RSI_14d", np.nan)),
        "stoch_k": 50.0,  # 仮置き（要追加実装）
        "momentum": 0.5,  # 仮置き
        "bollinger_upper_dist": 0.0,  # 仮置き
        "bollinger_lower_dist": 0.0,  # 仮置き
        "sentiment": row.get("News_Positive_Ratio", 0.5),
        "order_block": 0.0,  # 仮置き
        "liquidity_ratio": 1.0,  # 仮置き
        "interest_rate_diff": float(row.get("FEDFUNDS_Value", np.nan)),  # 利上げ系マクロ
        "cpi_change_rate": float(row.get("CPIAUCSL_Value", np.nan)),     # CPI
        "news_sentiment_score": row.get("News_Positive_Ratio", 0.5),
        "symbol": "USDJPY"
    }

# ---------- 3. Aurus AI予測デモ ----------
def aurus_batch_predict(feat_df: pd.DataFrame, aurus: AurusSingularis):
    """
    Plan層の特徴量DataFrame（複数日分）をAurusSingularisへ投入→シグナル出力
    """
    results = []
    for i, row in feat_df.iterrows():
        input_dict = plan_row_to_aurus_dict(row)
        proposal = aurus.propose(input_dict, decision_id=f"DEMO-{i+1}", caller="plan_to_aurus_demo")
        results.append({
            "date": row.get("Date"),
            "signal": proposal["signal"],
            "confidence": proposal["confidence"]
        })
    return pd.DataFrame(results)

# ---------- デモ実行部 ----------
if __name__ == "__main__":
    print("=== Plan層→AurusSingularis データ受け渡しDEMO ===")
    # 1. 特徴量データ生成
    feat_df = generate_plan_features(n_days=15)
    print("▶︎ Plan層特徴量サンプル（末尾3件）:\n", feat_df.tail(3)[["Date", "USDJPY_Close", "USDJPY_Volatility_5d", "USDJPY_RSI_14d", "News_Positive_Ratio"]])

    # 2. AurusSingularis AIインスタンス
    aurus_ai = AurusSingularis()
    # 3. 予測・シグナル出力
    aurus_result_df = aurus_batch_predict(feat_df, aurus_ai)
    print("\n▶︎ AurusSingularisのシグナル出力:\n", aurus_result_df)
