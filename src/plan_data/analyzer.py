# src/plan_data/analyzer.py

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List

class PlanAnalyzer:
    """
    PDCA-Planの根拠となる要因分析・特徴量抽出・説明ラベル化・LLM連携用サマリー生成クラス
    - 指標推移、戦略履歴、タグ別集計、異常/失敗事例など多角的に分析
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
        """
        指標特徴量を高度抽出
        ・急変動/ドリフト検知
        ・好調/不調戦略抽出
        ・危険なDD判定
        """
        features = {}
        df = self.stats_df.copy()

        # 基本統計
        features["win_rate_mean"] = win_mean = df["win_rate"].mean()
        features["win_rate_std"] = win_std = df["win_rate"].std()
        features["max_drawdown_mean"] = dd_mean = df["max_dd"].mean()
        features["num_trades_mean"] = numtr_mean = df["num_trades"].mean()

        # 直近傾向
        if not df.empty:
            last = df.iloc[-1]
            features["last_win_rate"] = last["win_rate"]
            features["last_max_dd"] = last["max_dd"]
        else:
            features["last_win_rate"] = None
            features["last_max_dd"] = None

        # 急変動検知（7日比較）
        if len(df) >= 7:
            winrate_7ago = df["win_rate"].iloc[-7]
            winrate_now = df["win_rate"].iloc[-1]
            delta7 = winrate_now - winrate_7ago
            features["win_rate_delta_7d"] = delta7
            features["win_rate_rapid_increase"] = delta7 > 3
            features["win_rate_rapid_decrease"] = delta7 < -3
        else:
            features["win_rate_delta_7d"] = None
            features["win_rate_rapid_increase"] = False
            features["win_rate_rapid_decrease"] = False

        # 好調/不調戦略抽出
        if "strategy" in df.columns and not df.empty:
            strat_perf = df.groupby("strategy")["win_rate"].mean()
            features["good_strategies"] = strat_perf[strat_perf > win_mean + win_std].index.tolist()
            features["bad_strategies"] = strat_perf[strat_perf < win_mean - win_std].index.tolist()
        else:
            features["good_strategies"] = []
            features["bad_strategies"] = []

        # 危険なDD判定
        if not df.empty and "max_dd" in df.columns:
            features["dangerous_max_dd"] = (df["max_dd"] < -15).sum()
        else:
            features["dangerous_max_dd"] = 0

        return features

    def make_explanation_labels(self, features: Dict[str, Any]) -> List[str]:
        """
        特徴量から説明ラベル（自然言語）を自動生成
        """
        labels = []
        if features.get("win_rate_rapid_increase"):
            labels.append("📈 勝率が直近7日間で大きく上昇しています。")
        if features.get("win_rate_rapid_decrease"):
            labels.append("📉 勝率が直近7日間で急落しています。")
        if features.get("dangerous_max_dd", 0) > 0:
            labels.append(f"⚠️ 最大ドローダウンが危険域（-15%以下）が{features['dangerous_max_dd']}件見られます。")
        if features.get("good_strategies"):
            gs = "、".join(features["good_strategies"][:3])
            labels.append(f"🌟 好調な戦略: {gs}")
        if features.get("bad_strategies"):
            bs = "、".join(features["bad_strategies"][:3])
            labels.append(f"🔻 不調な戦略: {bs}")
        return labels

    def generate_llm_summary(self, features: Dict[str, Any], labels: List[str]) -> str:
        """
        LLMプロンプトにそのまま使えるPlan根拠サマリーを生成
        """
        summary = "【PDCA Plan根拠サマリー】\n"
        if labels:
            summary += "・" + "\n・".join(labels) + "\n"
        summary += f"平均勝率: {features.get('win_rate_mean', 'N/A'):.2f}%、"
        summary += f"取引数平均: {features.get('num_trades_mean', 'N/A'):.1f}回\n"
        return summary

    def summarize_tag_trends(self) -> pd.DataFrame:
        """
        タグ別の勝率・取引数など集計
        """
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
        """
        異常/失敗パターンの分析
        """
        if self.anomaly_df is None or self.anomaly_df.empty:
            return pd.DataFrame()
        anomaly_summary = self.anomaly_df.groupby("anomaly_type").size().reset_index(name="count")
        anomaly_summary = anomaly_summary.sort_values("count", ascending=False)
        return anomaly_summary

    # 必要に応じてさらに分析関数追加OK

