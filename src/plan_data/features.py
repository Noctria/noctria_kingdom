# src/plan_data/features.py

import time
from typing import Optional, Dict, Iterable

import numpy as np
import pandas as pd

from plan_data.collector import ASSET_SYMBOLS  # 既定シンボル（任意で上書き可能）
from plan_data.observability import log_plan_run
from plan_data.trace import new_trace_id


# ==============
# 小ヘルパ
# ==============
def _to_numeric(df: pd.DataFrame, cols: Iterable[str]) -> pd.DataFrame:
    """指定列を数値化（errors='coerce'）。存在しない列は無視。"""
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


# ==============
# FeatureEngineer
# ==============
class FeatureEngineer:
    """
    PLAN 層の特徴量エンジニアリング。
    - 入力  : collector.collect_all() の DataFrame（snake_case）
    - 出力  : 同じ snake_case で特徴量を付加
    - ログ  : obs_plan_runs（phase="features"）
    """

    def __init__(
        self,
        symbols: Optional[Dict[str, str]] = None,
        *,
        # ウィンドウは後で検証できるようにパラメータ化（既定値は従来通り）
        ret_vol_win_short: int = 5,
        ret_vol_win_long: int = 20,
        rsi_window: int = 14,
        ma_fast: int = 5,
        ma_mid: int = 25,
        ma_slow: int = 75,
        news_base_win: int = 20,
        macro_spike_win: int = 12,
        macro_spike_minp: int = 6,
    ) -> None:
        self.symbols = symbols or ASSET_SYMBOLS
        self.ret_vol_win_short = ret_vol_win_short
        self.ret_vol_win_long = ret_vol_win_long
        self.rsi_window = rsi_window
        self.ma_fast = ma_fast
        self.ma_mid = ma_mid
        self.ma_slow = ma_slow
        self.news_base_win = news_base_win
        self.macro_spike_win = macro_spike_win
        self.macro_spike_minp = macro_spike_minp

    # --------------- 指標 ---------------
    def calc_rsi(self, series: pd.Series, window: int = 14) -> pd.Series:
        """RSI（inf/NaN 防御込み）。"""
        s = pd.to_numeric(series, errors="coerce")
        delta = s.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=window, min_periods=window).mean()
        avg_loss = loss.rolling(window=window, min_periods=window).mean()
        rs = avg_gain / avg_loss
        rs = rs.replace([np.inf, -np.inf], np.nan)  # 0割り防御
        rsi = 100 - (100 / (1 + rs))
        return rsi

    # --------------- メイン処理 ---------------
    def add_technical_features(
        self,
        df: pd.DataFrame,
        *,
        trace_id: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        入力: collector.collect_all() の出力（snake_case）
        出力: 同じ snake_case のまま、各 *_return, *_volatility_*, *_rsi_* 等を付与

        監視: 処理時間・行数・欠損率を obs_plan_runs に記録（phase="features"）
        """
        t0 = time.time()
        trace_id = trace_id or new_trace_id(symbol="MULTI", timeframe="1d")

        newdf = df.copy()

        # 'date' を保険で datetime 化（外部由来 DF でも壊れないように）
        if "date" in newdf.columns:
            newdf["date"] = pd.to_datetime(newdf["date"], errors="coerce")

        # 1) 市場系アセットの特徴量（close/volume があれば加工）
        for key in self.symbols:
            base = key.lower()
            c = f"{base}_close"
            v = f"{base}_volume"

            if c in newdf.columns:
                newdf[c] = pd.to_numeric(newdf[c], errors="coerce")

                # 収益率とボラ
                newdf[f"{base}_return"] = _safe_pct_change(newdf[c]).astype("float64")
                newdf[f"{base}_volatility_{self.ret_vol_win_short}d"] = (
                    newdf[f"{base}_return"].rolling(
                        window=self.ret_vol_win_short, min_periods=self.ret_vol_win_short
                    ).std()
                )
                newdf[f"{base}_volatility_{self.ret_vol_win_long}d"] = (
                    newdf[f"{base}_return"].rolling(
                        window=self.ret_vol_win_long, min_periods=self.ret_vol_win_long
                    ).std()
                )

                # RSI
                newdf[f"{base}_rsi_{self.rsi_window}d"] = self.calc_rsi(newdf[c], window=self.rsi_window)

                # 移動平均と GC / 並行トレンド
                ma_fast = newdf[c].rolling(window=self.ma_fast, min_periods=self.ma_fast).mean()
                ma_mid = newdf[c].rolling(window=self.ma_mid, min_periods=self.ma_mid).mean()
                ma_slow = newdf[c].rolling(window=self.ma_slow, min_periods=self.ma_slow).mean()

                gc_flag = (ma_fast > ma_mid) & (ma_fast.shift(1) <= ma_mid.shift(1))
                newdf[f"{base}_gc_flag"] = gc_flag.fillna(False).astype(int)

                newdf[f"{base}_ma{self.ma_fast}"] = ma_fast
                newdf[f"{base}_ma{self.ma_mid}"] = ma_mid
                newdf[f"{base}_ma{self.ma_slow}"] = ma_slow

                po_up = ((ma_fast > ma_mid) & (ma_mid > ma_slow)).astype("Int64")
                po_down = ((ma_fast < ma_mid) & (ma_mid < ma_slow)).astype("Int64")
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
            # 先頭 NaN が邪魔なら 0 埋め（用途次第）。今回は 0 埋めに寄せる。
            newdf["news_count_change"] = newdf["news_count"].diff().fillna(0.0)
            base_mean = newdf["news_count"].rolling(
                window=self.news_base_win, min_periods=max(10, self.news_base_win // 2)
            ).mean()
            newdf["news_spike_flag"] = (
                (newdf["news_count"] > base_mean * 2).fillna(False).astype(int)
            )

        if "news_positive" in newdf.columns and "news_negative" in newdf.columns:
            _to_numeric(newdf, ["news_positive", "news_negative"])
            denom = newdf.get("news_count", pd.Series(index=newdf.index, dtype="float64")) + 1e-6
            newdf["news_positive_ratio"] = (newdf["news_positive"] / denom).astype("float64")
            newdf["news_negative_ratio"] = (newdf["news_negative"] / denom).astype("float64")
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
                thr = diff.rolling(
                    window=self.macro_spike_win, min_periods=self.macro_spike_minp
                ).std() * 2
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


# ==============
# テスト実行
# ==============
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
