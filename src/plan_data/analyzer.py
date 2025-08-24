# src/plan_data/analyzer.py

import time
from typing import Optional, List, Dict

import numpy as np
import pandas as pd

from plan_data.observability import log_plan_run
from plan_data.trace import new_trace_id


class PlanAnalyzer:
    """
    P層の特徴量DataFrame（snake_case想定）から、軽量な要約特徴と説明ラベルを抽出。
    観測ログ（phase="analyzer"）も送る。
    """

    # ======= 閾値（チューニング用に定数化） =======
    WIN_RATE_DELTA7_THR = 3.0          # 勝率の7行差分がこのpp超なら急上昇
    NEWS_DELTA3_THR = 50.0             # ニュース件数の3行差分スパイク閾値
    ACTIVE_TRADES_THR = 20             # 取引回数がこの値超で「活発」
    DD_ABS_THR = 10.0                  # max_dd の絶対値がこの%超で「悪化」
    NEWS_COUNT_HIGH_THR = 200.0        # ニュース件数が多い判定

    def __init__(self, df: pd.DataFrame, *, trace_id: Optional[str] = None):
        """
        df: P層の特徴量DataFrame（snake_case想定）
        trace_id: 未指定なら自動生成（symbol="MULTI", timeframe="1d"）
        """
        # 数値列をできるだけ数値化（失敗はNaNに）
        self.df = df.copy()
        for c in self.df.columns:
            if c == "date":
                continue
            if self.df[c].dtype == "object":
                self.df[c] = pd.to_numeric(self.df[c], errors="coerce")

        self._trace_id = trace_id or new_trace_id(symbol="MULTI", timeframe="1d")

    # ======= ヘルパ =======
    def _last(self, s: pd.Series):
        """
        末尾値を安全に取得。末尾がNaNなら前方埋め（ffill）後の末尾を返す。
        取得不能なら NaN。
        """
        s = pd.to_numeric(s, errors="coerce")
        s_ffill = s.ffill()
        v = s_ffill.iloc[-1] if len(s_ffill) else np.nan
        return v if pd.notna(v) else np.nan

    def _delta(self, s: pd.Series, n: int):
        """
        “n行前との差分”を安全に取得。NaNは前方埋め（ffill）してから
        末尾値と n 行前の値の差を取る。先頭側に十分なデータが無ければ NaN。
        """
        if n < 1 or s is None or len(s) == 0:
            return np.nan
        s = pd.to_numeric(s, errors="coerce").ffill()
        if len(s) <= n:
            return np.nan
        last = s.iloc[-1]
        earlier = s.shift(n).iloc[-1]
        return float(last - earlier) if pd.notna(last) and pd.notna(earlier) else np.nan

    # NaN/NA を含む比較を安全にブールへ
    def _gt(self, value, threshold) -> bool:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return False
        try:
            return float(value) > float(threshold)
        except Exception:
            return False

    def _missing_ratio(self, df: Optional[pd.DataFrame]) -> float:
        """全体欠損率（'date' は除外）。空なら 1.0。"""
        if df is None or df.empty:
            return 1.0
        cols = [c for c in df.columns if c != "date"]
        if not cols:
            return 0.0
        total = len(df) * len(cols)
        if total <= 0:
            return 0.0
        return float(df[cols].isna().sum().sum()) / float(total)

    # ======= 特徴抽出 =======
    def extract_features(self) -> Dict:
        feats: Dict = {}

        # 例：勝率の変化をみる
        if "win_rate" in self.df.columns:
            last_wr = self._last(self.df["win_rate"])
            delta7 = self._delta(self.df["win_rate"], 7)
            feats["win_rate"] = last_wr
            feats["win_rate_delta7"] = delta7
            feats["win_rate_rapid_increase"] = self._gt(delta7, self.WIN_RATE_DELTA7_THR)  # NaNならFalse

        # 最大ドローダウン（値は負方向。絶対値で評価する方が可読）
        if "max_dd" in self.df.columns:
            last_dd = self._last(self.df["max_dd"])  # 例: -12.3
            feats["max_dd"] = last_dd
            feats["dd_worse_than_10"] = self._gt(abs(last_dd), self.DD_ABS_THR)

        # 取引回数
        if "num_trades" in self.df.columns:
            last_trades = self._last(self.df["num_trades"])
            feats["num_trades"] = last_trades
            feats["active_market"] = self._gt(last_trades, self.ACTIVE_TRADES_THR)

        # 市場関連の例（存在すれば）
        for col in ["usdjpy_close", "sp500_close", "vix_close"]:
            if col in self.df.columns:
                feats[col] = self._last(self.df[col])

        # ニュース件数とスパイク
        if "news_count" in self.df.columns:
            last_news = self._last(self.df["news_count"])
            delta3 = self._delta(self.df["news_count"], 3)
            feats["news_count"] = last_news
            feats["news_spike_recent"] = self._gt(delta3, self.NEWS_DELTA3_THR)

        # マクロ例
        for macro in ["cpiaucsl_value", "fedfunds_value", "unrate_value"]:
            if macro in self.df.columns:
                feats[macro] = self._last(self.df[macro])

        return feats

    # ======= ラベル生成 =======
    def make_explanation_labels(self, features: Dict) -> List[str]:
        labels: List[str] = []
        if features.get("win_rate_rapid_increase"):
            labels.append("勝率が直近で急上昇しています。")
        if features.get("dd_worse_than_10"):
            labels.append("ドローダウンが深く、リスクが高まっています。")
        if features.get("active_market"):
            labels.append("取引回数が多く、市場は活発です。")
        if self._gt(features.get("news_count", np.nan), self.NEWS_COUNT_HIGH_THR):
            labels.append("ニュース件数の増加が観測されます。")
        return labels

    # ======= 一括実行 + 観測ログ =======
    def analyze(self) -> Dict[str, object]:
        """
        特徴抽出と説明ラベル生成をまとめて実行し、観測ログ（phase="analyzer"）を残す。
        戻り値: {"features": dict, "labels": list}
        """
        t0 = time.time()
        feats = self.extract_features()
        labels = self.make_explanation_labels(feats)

        # 観測ログ（失敗しても本処理は継続）
        try:
            log_plan_run(
                None,  # env NOCTRIA_OBS_PG_DSN を使用
                phase="analyzer",
                rows=len(self.df),
                dur_sec=int(time.time() - t0),
                missing_ratio=self._missing_ratio(self.df),
                error_rate=0.0,  # TODO: 例外件数などを集計して反映
                trace_id=self._trace_id,
            )
        except Exception:
            pass

        return {"features": feats, "labels": labels}


# ======= テスト例 =======
if __name__ == "__main__":
    # 依存の都合で相対/絶対 import の両方に対応
    try:
        from src.plan_data.collector import PlanDataCollector  # type: ignore
        from src.plan_data.features import FeatureEngineer     # type: ignore
    except Exception:
        from plan_data.collector import PlanDataCollector
        from plan_data.features import FeatureEngineer

    base = PlanDataCollector().collect_all(lookback_days=90)
    feat = FeatureEngineer().add_technical_features(base)
    analyzer = PlanAnalyzer(feat)
    result = analyzer.analyze()

    print("features keys:", list(result["features"].keys())[:20], "...")
    print("labels:", result["labels"])
