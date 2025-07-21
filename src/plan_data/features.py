import pandas as pd
import numpy as np

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

        # 1. 市場系アセットの特徴量（従来通り）
        for key in self.symbols:
            c = f"{key}_Close"
            v = f"{key}_Volume"
            if c in newdf.columns:
                newdf[f"{key}_Return"] = newdf[c].pct_change()
                newdf[f"{key}_Volatility_5d"] = newdf[f"{key}_Return"].rolling(5).std()
                newdf[f"{key}_Volatility_20d"] = newdf[f"{key}_Return"].rolling(20).std()
                newdf[f"{key}_RSI_14d"] = self.calc_rsi(newdf[c], window=14)
                # ゴールデンクロス
                ma_short = newdf[c].rolling(5).mean()
                ma_long = newdf[c].rolling(25).mean()
                gc_flag = (ma_short > ma_long) & (ma_short.shift(1) <= ma_long.shift(1))
                newdf[f"{key}_GC_Flag"] = gc_flag.astype(int)
                # 3本MAパーフェクトオーダー
                ma_mid = newdf[c].rolling(25).mean()
                ma_longer = newdf[c].rolling(75).mean()
                newdf[f"{key}_MA5"] = ma_short
                newdf[f"{key}_MA25"] = ma_mid
                newdf[f"{key}_MA75"] = ma_longer
                po_up = ((ma_short > ma_mid) & (ma_mid > ma_longer)).astype(int)
                po_down = ((ma_short < ma_mid) & (ma_mid < ma_longer)).astype(int)
                newdf[f"{key}_PO_UP"] = po_up
                newdf[f"{key}_PO_DOWN"] = po_down
            if v in newdf.columns:
                newdf[f"{key}_Volume_MA5"] = newdf[v].rolling(5).mean()
                newdf[f"{key}_Volume_MA20"] = newdf[v].rolling(20).mean()
                avg20 = newdf[f"{key}_Volume_MA20"]
                newdf[f"{key}_Volume_Spike"] = ((newdf[v] > avg20 * 2) & (avg20 > 0)).astype(int)

        # 2. ニュース件数・センチメント系
        if "News_Count" in newdf.columns:
            newdf["News_Count_Change"] = newdf["News_Count"].diff()
            newdf["News_Spike_Flag"] = (newdf["News_Count"] > newdf["News_Count"].rolling(20).mean() * 2).astype(int)
        if "News_Positive" in newdf.columns and "News_Negative" in newdf.columns:
            newdf["News_Positive_Ratio"] = newdf["News_Positive"] / (newdf["News_Count"] + 1e-6)
            newdf["News_Negative_Ratio"] = newdf["News_Negative"] / (newdf["News_Count"] + 1e-6)
            # ポジ/ネガ優勢フラグ
            newdf["News_Positive_Lead"] = (newdf["News_Positive"] > newdf["News_Negative"]).astype(int)
            newdf["News_Negative_Lead"] = (newdf["News_Negative"] > newdf["News_Positive"]).astype(int)

        # 3. マクロ経済指標系（例：CPI、失業率、政策金利）
        for macro in ["CPIAUCSL_Value", "UNRATE_Value", "FEDFUNDS_Value"]:
            if macro in newdf.columns:
                newdf[f"{macro}_Diff"] = newdf[macro].diff()
                newdf[f"{macro}_Spike_Flag"] = (np.abs(newdf[f"{macro}_Diff"]) > newdf[f"{macro}_Diff"].rolling(12).std() * 2).astype(int)

        # 4. 経済カレンダー・イベントフラグ（例: FOMC, CPI, NFP...）
        # カラムが存在していれば「イベント日」フラグそのまま
        event_cols = [c for c in newdf.columns if c.upper() in {"FOMC", "CPI", "NFP", "ECB", "BOJ", "GDP"}]
        for event in event_cols:
            # イベント発生日で1, それ以外は0 or nan
            newdf[f"{event}_Today_Flag"] = (newdf[event] == 1).astype(int)

        return newdf

# テスト例
if __name__ == "__main__":
    from collector import ASSET_SYMBOLS
    import sys
    sys.path.append(".")
    import collector
    base_df = collector.PlanDataCollector().collect_all(lookback_days=180)
    fe = FeatureEngineer(ASSET_SYMBOLS)
    feat_df = fe.add_technical_features(base_df)
    pd.set_option('display.max_columns', 80)
    print(feat_df.tail(5))
