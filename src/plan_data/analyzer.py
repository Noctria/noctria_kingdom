# src/plan_data/analyzer.py

import pandas as pd
import numpy as np
import json
from typing import List, Dict, Any, Optional

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

    def feature_importance(self) -> Dict[str, float]:
        """
        シンプルな特徴量重要度の例（カテゴリごとの勝率平均/最大DDなど）
        """
        result = {}
        if "tags" in self.stats_df.columns:
            tag_win = self.stats_df.explode("tags").groupby("tags")["win_rate"].mean().sort_values(ascending=False)
            result["tag_win_rate"] = tag_win.to_dict()
        if "max_drawdown" in self.stats_df.columns:
            result["mean_max_drawdown"] = float(self.stats_df["max_drawdown"].mean())
        if "profit_factor" in self.stats_df.columns:
            result["mean_profit_factor"] = float(self.stats_df["profit_factor"].mean())
        return result

    def detect_declining_tags(self, window: int = 10) -> List[str]:
        """
        時系列的に勝率が低下しているタグを検出（最近10件の移動平均で判断）
        """
        if "tags" not in self.stats_df.columns or "win_rate" not in self.stats_df.columns:
            return []
        declining_tags = []
        tag_df = self.stats_df.explode("tags")
        for tag in tag_df["tags"].unique():
            tag_hist = tag_df[tag_df["tags"] == tag].sort_values("evaluated_at")
            if len(tag_hist) < window * 2:
                continue
            win_ma = tag_hist["win_rate"].rolling(window).mean()
            if win_ma.iloc[-1] < win_ma.iloc[window-1]:
                declining_tags.append(tag)
        return declining_tags

    def summarize_failures(self, max_items: int = 5) -> List[Dict[str, Any]]:
        """
        採用されなかった or 大きなドローダウン/損失戦略の特徴例を抽出
        """
        if "result" not in self.stats_df.columns or "max_drawdown" not in self.stats_df.columns:
            return []
        failed = self.stats_df[(self.stats_df["result"] == "❌ 不採用") | (self.stats_df["max_drawdown"] > 20)]
        samples = failed.head(max_items).to_dict(orient="records")
        return samples

    def analyze(self) -> Dict[str, Any]:
        """
        総合要因分析のまとめ（Plan根拠のAI用プロンプトに渡す用）
        """
        return {
            "feature_importance": self.feature_importance(),
            "declining_tags": self.detect_declining_tags(),
            "failure_examples": self.summarize_failures(),
            "actlog_stats": self.actlog_df.describe().to_dict() if self.actlog_df is not None else {},
            "anomalies": self.anomaly_df.to_dict(orient="records") if self.anomaly_df is not None else []
        }

# --- テスト例（データがある場合） ---
if __name__ == "__main__":
    # テストデータのロード
    try:
        stats = pd.read_json("data/stats/veritas_eval_result.json", lines=True)
    except Exception:
        stats = pd.DataFrame()

    analyzer = PlanAnalyzer(stats)
    analysis = analyzer.analyze()
    print(json.dumps(analysis, ensure_ascii=False, indent=2))
