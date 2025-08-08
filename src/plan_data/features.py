# src/plan_data/features.py

import pandas as pd
import numpy as np
from plan_data.feature_spec import FEATURE_SPEC
from plan_data.collector import ASSET_SYMBOLS  # 必要に応じて調整

def align_to_feature_spec(df: pd.DataFrame) -> pd.DataFrame:
    """feature_spec.pyに準拠したカラム順・型・補完でDataFrameを整形"""
    columns = list(FEATURE_SPEC.keys())
    for col in columns:
        if col not in df.columns:
            df[col] = pd.NA
    for col in columns:
        try:
            dtype = FEATURE_SPEC[col]["type"]
            df[col] = df[col].astype(dtype)
        except Exception:
            pass
    return df[columns]

class FeatureEngineer:
    def __init__(self, symbols: dict = None):
        """
        symbols: ASSET_SYMBOLSなどのdict（マーケット系シンボルのみ）
        """
        self.symbols = symbols or {}

    def calc_rsi(self, series: pd.Series, window: int = 14) -> pd.Series:
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window).mean()
        avg_loss = loss.rolling(window).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def add_technical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        newdf = df.copy()

        # 1. 市場系アセットの特徴量
        for key in self.symbols:
            # 小文字・アンダースコアへ統一
            key_l = key.lower()
            c = f"{key_l}_close"
            v = f"{key_l}_volume"
            if c in newdf.columns:
                newdf[f"{key_l}_return"] = newdf[c].pct_change()
                newdf[f"{key_l}_volatility_5d"] = newdf[f"{key_l}_return"].rolling(5).std()
                newdf[f"{key_l}_volatility_20d"] = newdf[f"{key_l}_return"].rolling(20).std()
                newdf[f"{key_l}_rsi_14d"] = self.calc_rsi(newdf[c], window=14)
                ma_short = newdf[c].rolling(5).mean()
                ma_long = newdf[c].rolling(25).mean()
                gc_flag = (ma_short > ma_long) & (ma_short.shift(1) <= ma_long.shift(1))
                newdf[f"{key_l}_gc_flag"] = gc_flag.astype(int)
                ma_mid = newdf[c].rolling(25).mean()
                ma_longer = newdf[c].rolling(75).mean()
                newdf[f"{key_l}_ma5"] = ma_short
                newdf[f"{key_l}_ma25"] = ma_mid
                newdf[f"{key_l}_ma75"] = ma_longer
                po_up = ((ma_short > ma_mid) & (ma_mid > ma_longer)).astype(int)
                po_down = ((ma_short < ma_mid) & (ma_mid < ma_longer)).astype(int)
                newdf[f"{key_l}_po_up"] = po_up
                newdf[f"{key_l}_po_down"] = po_down
            if v in newdf.columns:
                newdf[f"{key_l}_volume_ma5"] = newdf[v].rolling(5).mean()
                newdf[f"{key_l}_volume_ma20"] = newdf[v].rolling(20).mean()
                avg20 = newdf[f"{key_l}_volume_ma20"]
                newdf[f"{key_l}_volume_spike"] = ((newdf[v] > avg20 * 2) & (avg20 > 0)).astype(int)

        # 2. ニュース件数・センチメント系
        if "news_count" in newdf.columns:
            newdf["news_count_change"] = newdf["news_count"].diff()
            newdf["news_spike_flag"] = (newdf["news_count"] > newdf["news_count"].rolling(20).mean() * 2).astype(int)
        if "news_positive" in newdf.columns and "news_negative" in newdf.columns:
            newdf["news_positive_ratio"] = newdf["news_positive"] / (newdf["news_count"] + 1e-6)
            newdf["news_negative_ratio"] = newdf["news_negative"] / (newdf["news_count"] + 1e-6)
            newdf["news_positive_lead"] = (newdf["news_positive"] > newdf["news_negative"]).astype(int)
            newdf["news_negative_lead"] = (newdf["news_negative"] > newdf["news_positive"]).astype(int)

        # 3. マクロ経済指標系（例：CPI、失業率、政策金利）
        for macro in ["cpiaucsl_value", "unrate_value", "fedfunds_value"]:
            if macro in newdf.columns:
                newdf[f"{macro}_diff"] = newdf[macro].diff()
                newdf[f"{macro}_spike_flag"] = (np.abs(newdf[f"{macro}_diff"]) > newdf[f"{macro}_diff"].rolling(12).std() * 2).astype(int)

        # 4. 経済カレンダー・イベントフラグ（例: fomc, cpi, nfp...）
        event_cols = [c for c in newdf.columns if c.lower() in {"fomc", "cpi", "nfp", "ecb", "boj", "gdp"}]
        for event in event_cols:
            newdf[f"{event.lower()}_today_flag"] = (newdf[event] == 1).astype(int)

        # 必ずfeature_spec準拠に変換
        return align_to_feature_spec(newdf)

# テスト例
if __name__ == "__main__":
    import sys
    sys.path.append(".")
    from src.plan_data.collector import PlanDataCollector, ASSET_SYMBOLS
    base_df = PlanDataCollector().collect_all(lookback_days=180)
    fe = FeatureEngineer(ASSET_SYMBOLS)
    feat_df = fe.add_technical_features(base_df)
    pd.set_option('display.max_columns', 80)
    print(feat_df.tail(5))
