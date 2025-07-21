# src/plan_data/analyzer.py

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any

class PlanAnalyzer:
    """
    PDCA-Planの根拠となる要因分析・特徴量抽出クラス
    - 指標推移、戦略履歴、タグ別集計、異常/失敗事例、ドリフト等をもとに
    - 「なぜ良かったか/悪かったか」「注目すべき特徴・傾向」などを抽出する
    """

    def __init__(
        self,
        stats_df: pd.DataFrame,
        actlog_df: Optional[pd.DataFrame] = None,
        anomaly_df: Optional[pd.DataFrame] = None
    ):
        self.stats_df = stats_df
        self.actlog_df = actlog_df
        self.anomaly_df = anomaly_df

    def extract_features(self) -> Dict[str, Any]:
        """ 指標・傾向などの特徴量抽出 """
        features = {}

        # 勝率の基本統計
        features["win_rate_mean"] = self.stats_df["win_rate"].mean()
        features["win_rate_std"] = self.stats_df["win_rate"].std()
        features["max_drawdown_mean"] = self.stats_df["max_dd"].mean()
        features["num_trades_mean"] = self.stats_df["num_trades"].mean()

        # 直近傾向
        last = self.stats_df.iloc[-1]
        features["last_win_rate"] = last["win_rate"]
        features["last_max_dd"] = last["max_dd"]

        # 急変動検知
        if len(self.stats_df) >= 2:
            delta = self.stats_df["win_rate"].iloc[-1] - self.stats_df["win_rate"].iloc[-2]
            features["win_rate_delta"] = delta
            features["win_rate_trend"] = (
                "上昇" if delta > 2 else "下降" if delta < -2 else "横ばい"
            )
        else:
            features["win_rate_delta"] = None
            features["win_rate_trend"] = "データ不足"

        return features

    def summarize_tag_trends(self) -> pd.DataFrame:
        """ タグ別の勝率・取引数など集計 """
        if "tag" not in self.stats_df.columns:
            return pd.DataFrame()
        tag_stats = self.stats_df.groupby("tag").agg(
            win_rate_mean=("win_rate", "mean"),
            max_dd_mean=("max_dd", "mean"),
            num_trades_sum=("num_trades", "sum"),
            strategy_count=("strategy", "nunique"),
        ).reset_index()
        tag_stats = tag_stats.sort_values("win_rate_mean", ascending=False)
        return tag_stats

    def analyze_anomalies(self) -> pd.DataFrame:
        """ 異常/失敗パターンの分析 """
        if self.anomaly_df is None or self.anomaly_df.empty:
            return pd.DataFrame()
        anomaly_summary = self.anomaly_df.groupby("anomaly_type").size().reset_index(name="count")
        anomaly_summary = anomaly_summary.sort_values("count", ascending=False)
        return anomaly_summary

    # 必要に応じてさらに分析関数追加OK
