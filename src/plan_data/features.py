# src/plan_data/features.py

import pandas as pd

class FeatureEngineer:
    def __init__(self, symbols: dict):
        self.symbols = symbols

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
        for key in self.symbols:
            c = f"{key}_Close"
            v = f"{key}_Volume"
            # リターン・ボラ
            if c in newdf.columns:
                newdf[f"{key}_Return"] = newdf[c].pct_change()
                newdf[f"{key}_Volatility_5d"] = newdf[f"{key}_Return"].rolling(5).std()
                newdf[f"{key}_Volatility_20d"] = newdf[f"{key}_Return"].rolling(20).std()
                # RSI
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
            # 出来高
            if v in newdf.columns:
                newdf[f"{key}_Volume_MA5"] = newdf[v].rolling(5).mean()
                newdf[f"{key}_Volume_MA20"] = newdf[v].rolling(20).mean()
                avg20 = newdf[f"{key}_Volume_MA20"]
                newdf[f"{key}_Volume_Spike"] = ((newdf[v] > avg20 * 2) & (avg20 > 0)).astype(int)
        return newdf

# テスト例
if __name__ == "__main__":
    from collector import ASSET_SYMBOLS
    import sys
    sys.path.append(".")  # 必要に応じてパス調整
    import collector
    base_df = collector.PlanDataCollector().collect_all(lookback_days=180)
    fe = FeatureEngineer(ASSET_SYMBOLS)
    feat_df = fe.add_technical_features(base_df)
    print(feat_df.tail(5))
