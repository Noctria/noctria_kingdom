# src/plan_data/features.py

import time
import pandas as pd
import numpy as np
from typing import Optional, Dict

from plan_data.collector import ASSET_SYMBOLS  # 既定シンボル（任意で上書き可能）
from plan_data.observability import log_plan_run
from plan_data.trace import new_trace_id


def _to_numeric(df: pd.DataFrame, cols) -> pd.DataFrame:
    """指定列を数値化（errors='coerce'）"""
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _safe_pct_change(s: pd.Series) -> pd.Series:
    """
    pandas FutureWarning 回避のため fill_method=None を明示。
    先頭は NaN のまま。非数値は事前に数値化してから渡すこと。
    """
    return s.pct_change(fill_method=None)


def _missing_ratio(df: Optional[pd.DataFrame]) -> float:
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


class FeatureEngineer:
    def __init__(self, symbols: Dict[str, str] = None):
        """
        symbols: ASSET_SYMBOLS 互換の dict（{"USDJPY": "JPY=X", ...} のキー名を使う）
        """
        self.symbols = symbols or ASSET_SYMBOLS

    def calc_rsi(self, series: pd.Series, window: int = 14) -> pd.Series:
        # 数値に寄せる
        s = pd.to_numeric(series, errors="coerce")
        delta = s.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=window, min_periods=window).mean()
        avg_loss = loss.rolling(window=window, min_periods=window).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def add_technical_features(
        self,
        df: pd.DataFrame,
        *,
        trace_id: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        入力: collector.collect_all() の出力（snake_case）
        出力: 同じ snake_case のまま、各 *_return, *_volatility_*, *_rsi_14d 等を付与

        監視: 処理時間・行数・欠損率を obs_plan_runs に記録（phase="features"）
        """
        t0 = time.time()
        trace_id = trace_id or new_trace_id(symbol="MULTI", timeframe="1d")

        newdf = df.copy()

        # 1) 市場系アセットの特徴量（close/volume があれば加工）
        for key in self.symbols:
            base = key.lower()
            c = f"{base}_close"
            v = f"{base}_volume"

            if c in newdf.columns:
                # 数値化
                newdf[c] = pd.to_numeric(newdf[c], errors="coerce")

                # 収益率とボラ
                newdf[f"{base}_return"] = _safe_pct_change(newdf[c])
                newdf[f"{base}_volatility_5d"] = (
                    newdf[f"{base}_return"].rolling(window=5, min_periods=5).std()
                )
                newdf[f"{base}_volatility_20d"] = (
                    newdf[f"{base}_return"].rolling(window=20, min_periods=20).std()
                )

                # RSI
                newdf[f"{base}_rsi_14d"] = self.calc_rsi(newdf[c], window=14)

                # 移動平均とGCフラグ
                ma5 = newdf[c].rolling(window=5, min_periods=5).mean()
                ma25 = newdf[c].rolling(window=25, min_periods=25).mean()
                ma75 = newdf[c].rolling(window=75, min_periods=75).mean()

                gc_flag = (ma5 > ma25) & (ma5.shift(1) <= ma25.shift(1))
                newdf[f"{base}_gc_flag"] = gc_flag.fillna(False).astype(int)

                newdf[f"{base}_ma5"] = ma5
                newdf[f"{base}_ma25"] = ma25
                newdf[f"{base}_ma75"] = ma75

                po_up = ((ma5 > ma25) & (ma25 > ma75)).astype("Int64")
                po_down = ((ma5 < ma25) & (ma25 < ma75)).astype("Int64")
                newdf[f"{base}_po_up"] = po_up
                newdf[f"{base}_po_down"] = po_down

            if v in newdf.columns:
                newdf[v] = pd.to_numeric(newdf[v], errors="coerce")
                vol_ma5 = newdf[v].rolling(window=5, min_periods=5).mean()
                vol_ma20 = newdf[v].rolling(window=20, min_periods=20).mean()
                newdf[f"{base}_volume_ma5"] = vol_ma5
                newdf[f"{base}_volume_ma20"] = vol_ma20
                newdf[f"{base}_volume_spike"] = (
                    ((newdf[v] > vol_ma20 * 2) & (vol_ma20 > 0)).fillna(False).astype(int)
                )

        # 2) ニュース件数・センチメント
        if "news_count" in newdf.columns:
            newdf["news_count"] = pd.to_numeric(newdf["news_count"], errors="coerce")
            newdf["news_count_change"] = newdf["news_count"].diff()
            base_mean20 = newdf["news_count"].rolling(window=20, min_periods=10).mean()
            newdf["news_spike_flag"] = (
                (newdf["news_count"] > base_mean20 * 2).fillna(False).astype(int)
            )

        if "news_positive" in newdf.columns and "news_negative" in newdf.columns:
            _to_numeric(newdf, ["news_positive", "news_negative"])
            denom = (newdf.get("news_count", pd.Series(index=newdf.index, dtype="float64")) + 1e-6)
            newdf["news_positive_ratio"] = newdf["news_positive"] / denom
            newdf["news_negative_ratio"] = newdf["news_negative"] / denom
            newdf["news_positive_lead"] = (
                (newdf["news_positive"] > newdf["news_negative"]).fillna(False).astype(int)
            )
            newdf["news_negative_lead"] = (
                (newdf["news_negative"] > newdf["news_positive"]).fillna(False).astype(int)
            )

        # 3) マクロ（CPI/UNRATE/FEDFUNDS）
        for macro in ["cpiaucsl_value", "unrate_value", "fedfunds_value"]:
            if macro in newdf.columns:
                newdf[macro] = pd.to_numeric(newdf[macro], errors="coerce")
                diff = newdf[macro].diff()
                newdf[f"{macro}_diff"] = diff
                thr = diff.rolling(window=12, min_periods=6).std() * 2
                newdf[f"{macro}_spike_flag"] = (np.abs(diff) > thr).fillna(False).astype(int)

        # 4) 経済イベント（fomc, cpi, nfp, ...）: 0/1 を Int64 で保持、today_flag も付与
        event_candidates = {"fomc", "cpi", "nfp", "ecb", "boj", "gdp"}
        event_cols = [c for c in newdf.columns if c.lower() in event_candidates]
        for c in event_cols:
            cc = c.lower()
            # 0/1/True/False を 0/1(Int64) に寄せる
            if newdf[c].dropna().isin([0, 1, True, False]).all():
                newdf[c] = newdf[c].astype("Int64")
            # 当日フラグ（この DF は日次まとめなので 当該列==1 をそのまま today_flag とする）
            newdf[f"{cc}_today_flag"] = (newdf[c] == 1).astype("Int64")

        # 最後に date 昇順＆重複除去（保険）
        if "date" in newdf.columns:
            newdf = newdf.sort_values("date").drop_duplicates(subset=["date"]).reset_index(drop=True)

        # 観測ログ（失敗しても継続）
        try:
            log_plan_run(
                None,  # env NOCTRIA_OBS_PG_DSN を使用
                phase="features",
                rows=len(newdf),
                dur_sec=int(time.time() - t0),
                missing_ratio=_missing_ratio(newdf),
                error_rate=0.0,  # TODO: 個別変換エラーを集計して反映
                trace_id=trace_id,
            )
        except Exception:
            pass

        # FEATURE_SPEC へは寄せず、そのまま snake_case のまま返す
        return newdf


# テスト例
if __name__ == "__main__":
    # 直接実行時の依存解決（実行環境により import パスを調整してください）
    try:
        from src.plan_data.collector import PlanDataCollector  # type: ignore
    except Exception:
        from plan_data.collector import PlanDataCollector

    base_df = PlanDataCollector().collect_all(lookback_days=180)
    fe = FeatureEngineer(ASSET_SYMBOLS)
    feat_df = fe.add_technical_features(base_df)

    pd.set_option("display.max_columns", 120)
    print("columns:", feat_df.columns.tolist())
    print(feat_df.tail(5))
