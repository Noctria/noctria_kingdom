# src/plan_data/analyzer.py

import numpy as np
import pandas as pd

class PlanAnalyzer:
    def __init__(self, df: pd.DataFrame):
        # 数値列をできるだけ数値化（失敗はNaNに）
        self.df = df.copy()
        for c in self.df.columns:
            if c == "date":
                continue
            if self.df[c].dtype == "object":
                self.df[c] = pd.to_numeric(self.df[c], errors="coerce")

    # 安全に末尾値を取得
    def _last(self, s: pd.Series):
        s = pd.to_numeric(s, errors="coerce")
        s = s.dropna()
        return s.iloc[-1] if len(s) else np.nan

    # 安全に n 日（行）差分を取得（末尾と n+1 個前の差）
    def _delta(self, s: pd.Series, n: int):
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) >= (n + 1):
            return float(s.iloc[-1] - s.iloc[-(n + 1)])
        return np.nan

    # NaN/NA を含む比較を安全にブールへ
    def _gt(self, value, threshold) -> bool:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return False
        try:
            return float(value) > float(threshold)
        except Exception:
            return False

    def extract_features(self) -> dict:
        feats = {}

        # 例：勝率の変化をみる
        if "win_rate" in self.df.columns:
            last_wr = self._last(self.df["win_rate"])
            delta7 = self._delta(self.df["win_rate"], 7)
            feats["win_rate"] = last_wr
            feats["win_rate_delta7"] = delta7
            feats["win_rate_rapid_increase"] = self._gt(delta7, 3)  # NaNならFalse

        # 最大ドローダウン（より小さいほど悪い）
        if "max_dd" in self.df.columns:
            last_dd = self._last(self.df["max_dd"])
            feats["max_dd"] = last_dd
            # 例：直近のドローダウンが閾値より悪化か
            feats["dd_worse_than_10"] = self._gt(-last_dd, 10)  # max_dd が -10 以下で True 相当

        # 取引回数
        if "num_trades" in self.df.columns:
            last_trades = self._last(self.df["num_trades"])
            feats["num_trades"] = last_trades
            feats["active_market"] = self._gt(last_trades, 20)

        # 市場関連の例（存在すれば）
        for col in ["usdjpy_close", "sp500_close", "vix_close"]:
            if col in self.df.columns:
                last_val = self._last(self.df[col])
                feats[col] = last_val

        # ニュース件数
        if "news_count" in self.df.columns:
            last_news = self._last(self.df["news_count"])
            delta3 = self._delta(self.df["news_count"], 3)
            feats["news_count"] = last_news
            feats["news_spike_recent"] = self._gt(delta3, 50)

        # マクロ例
        for macro in ["cpiaucsl_value", "fedfunds_value", "unrate_value"]:
            if macro in self.df.columns:
                feats[macro] = self._last(self.df[macro])

        return feats

    def make_explanation_labels(self, features: dict) -> list:
        labels = []
        if features.get("win_rate_rapid_increase"):
            labels.append("勝率が直近で急上昇しています。")
        if features.get("dd_worse_than_10"):
            labels.append("ドローダウンが深く、リスクが高まっています。")
        if features.get("active_market"):
            labels.append("取引回数が多く、市場は活発です。")
        if self._gt(features.get("news_count", np.nan), 200):
            labels.append("ニュース件数の増加が観測されます。")
        return labels
