import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List

class PlanAnalyzer:
    """
    PDCA-Plan根拠となる要因分析・特徴量抽出・説明ラベル化・LLM連携サマリー生成クラス
    - マクロ・ニュース・イベント系も自動判定
    """

    def __init__(
        self,
        stats_df: pd.DataFrame,
        actlog_df: Optional[pd.DataFrame] = None,
        anomaly_df: Optional[pd.DataFrame] = None,
    ):
        self.stats_df = stats_df
        self.actlog_df = actlog_df
        self.anomaly_df = anomaly_df

    def extract_features(self) -> Dict[str, Any]:
        """
        指標特徴量の高度抽出（ニュース・マクロ・イベントも柔軟分析）
        """
        features = {}
        df = self.stats_df.copy()

        # 基本統計
        features["win_rate_mean"] = win_mean = df["win_rate"].mean() if "win_rate" in df else np.nan
        features["win_rate_std"] = win_std = df["win_rate"].std() if "win_rate" in df else np.nan
        features["max_drawdown_mean"] = dd_mean = df["max_dd"].mean() if "max_dd" in df else np.nan
        features["num_trades_mean"] = numtr_mean = df["num_trades"].mean() if "num_trades" in df else np.nan

        # 直近傾向
        if not df.empty:
            last = df.iloc[-1]
            features["last_win_rate"] = last.get("win_rate", None)
            features["last_max_dd"] = last.get("max_dd", None)
        else:
            features["last_win_rate"] = None
            features["last_max_dd"] = None

        # 急変動検知（7日比較）
        if "win_rate" in df and len(df) >= 7:
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

        # ニュース件数の急増/急減フラグ
        if "News_Count" in df.columns and len(df) >= 7:
            news_now = df["News_Count"].iloc[-1]
            news_7ago = df["News_Count"].iloc[-7]
            news_delta = news_now - news_7ago
            features["news_count_delta_7d"] = news_delta
            features["news_count_spike"] = news_delta > df["News_Count"].rolling(20).std().iloc[-1] * 2
        else:
            features["news_count_delta_7d"] = None
            features["news_count_spike"] = False

        # ポジ/ネガニュース優勢のフラグ
        if "News_Positive" in df.columns and "News_Negative" in df.columns:
            pos_now = df["News_Positive"].iloc[-1]
            neg_now = df["News_Negative"].iloc[-1]
            features["news_positive_lead"] = pos_now > neg_now
            features["news_negative_lead"] = neg_now > pos_now

        # マクロ経済指標の急変（例: CPI、失業率、金利...）
        macro_cols = [c for c in df.columns if c.endswith("_Value")]
        for mc in macro_cols:
            if len(df) >= 7:
                now = df[mc].iloc[-1]
                ago = df[mc].iloc[-7]
                delta = now - ago
                std = df[mc].rolling(20).std().iloc[-1] if df[mc].rolling(20).std().notna().any() else 1
                features[f"{mc}_delta_7d"] = delta
                features[f"{mc}_spike"] = abs(delta) > std * 2
            else:
                features[f"{mc}_delta_7d"] = None
                features[f"{mc}_spike"] = False

        # 好調/不調戦略抽出
        if "strategy" in df.columns and "win_rate" in df.columns and not df.empty:
            strat_perf = df.groupby("strategy")["win_rate"].mean()
            features["good_strategies"] = strat_perf[strat_perf > win_mean + win_std].index.tolist()
            features["bad_strategies"] = strat_perf[strat_perf < win_mean - win_std].index.tolist()
        else:
            features["good_strategies"] = []
            features["bad_strategies"] = []

        # 危険なDD判定
        if "max_dd" in df.columns and not df.empty:
            features["dangerous_max_dd"] = (df["max_dd"] < -15).sum()
        else:
            features["dangerous_max_dd"] = 0

        # 主要イベント日フラグ（例: FOMC, CPI, NFP）
        event_cols = [c for c in df.columns if c.upper() in {"FOMC", "CPI", "NFP", "ECB", "BOJ", "GDP"}]
        for event in event_cols:
            features[f"{event}_today"] = bool(df[event].iloc[-1] == 1)

        return features

    def make_explanation_labels(self, features: Dict[str, Any]) -> List[str]:
        """
        特徴量から自然言語ラベルを自動生成（マクロ・ニュース系も）
        """
        labels = []
        # 勝率・DD
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
        # ニュース系
        if features.get("news_count_spike"):
            labels.append("📰 ニュース件数が直近で急増しています（市場の話題性が高まっています）。")
        if features.get("news_positive_lead"):
            labels.append("🟢 ポジティブなニュースが優勢です。")
        if features.get("news_negative_lead"):
            labels.append("🔴 ネガティブなニュースが優勢です。")
        # マクロ指標系
        for macro in [k for k in features if k.endswith("_spike")]:
            if features[macro]:
                label = macro.replace("_spike", "").replace("_Value", "")
                labels.append(f"📊 {label}が直近で大きく変動しています。")
        # イベント系
        for k, v in features.items():
            if k.endswith("_today") and v:
                event = k.replace("_today", "")
                labels.append(f"⏰ 今日は重要イベント日（{event}）です。")
        return labels

    def generate_llm_summary(self, features: Dict[str, Any], labels: List[str]) -> str:
        """
        LLMプロンプト用Plan根拠サマリー
        """
        summary = "【PDCA Plan根拠サマリー】\n"
        if labels:
            summary += "・" + "\n・".join(labels) + "\n"
        summary += f"平均勝率: {features.get('win_rate_mean', 'N/A'):.2f}%、"
        summary += f"取引数平均: {features.get('num_trades_mean', 'N/A'):.1f}回\n"
        return summary

    def summarize_tag_trends(self) -> pd.DataFrame:
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
        if self.anomaly_df is None or self.anomaly_df.empty:
            return pd.DataFrame()
        anomaly_summary = self.anomaly_df.groupby("anomaly_type").size().reset_index(name="count")
        anomaly_summary = anomaly_summary.sort_values("count", ascending=False)
        return anomaly_summary

    # ▼▼▼ FREDデータ活用分析 ▼▼▼

    def analyze_by_fred_condition(
        self, 
        merged_df: pd.DataFrame, 
        fred_col: str, 
        threshold: float = None
    ) -> dict:
        if fred_col not in merged_df.columns:
            return {}

        th = threshold if threshold is not None else merged_df[fred_col].median()
        high_cond = merged_df[fred_col] >= th
        low_cond = merged_df[fred_col] < th

        summary = {
            f"{fred_col}_high": {
                "count": int(high_cond.sum()),
                "win_rate_mean": merged_df.loc[high_cond, "win_rate"].mean() if "win_rate" in merged_df else np.nan,
                "max_dd_mean": merged_df.loc[high_cond, "max_dd"].mean() if "max_dd" in merged_df else np.nan,
                "num_trades_mean": merged_df.loc[high_cond, "num_trades"].mean() if "num_trades" in merged_df else np.nan,
            },
            f"{fred_col}_low": {
                "count": int(low_cond.sum()),
                "win_rate_mean": merged_df.loc[low_cond, "win_rate"].mean() if "win_rate" in merged_df else np.nan,
                "max_dd_mean": merged_df.loc[low_cond, "max_dd"].mean() if "max_dd" in merged_df else np.nan,
                "num_trades_mean": merged_df.loc[low_cond, "num_trades"].mean() if "num_trades" in merged_df else np.nan,
            }
        }
        return summary

    def correlation_with_fred(self, merged_df: pd.DataFrame, fred_col: str) -> Optional[float]:
        if fred_col not in merged_df.columns or "win_rate" not in merged_df.columns:
            return None
        return merged_df[["win_rate", fred_col]].corr().iloc[0, 1]

    # 追加の分析関数も随時対応OK

