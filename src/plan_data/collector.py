# src/plan_data/collector.py

import os
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional

try:
    import yfinance as yf
except ImportError:
    raise ImportError("yfinance が必要です: pip install yfinance")

ASSET_SYMBOLS = {
    "USDJPY": "JPY=X",
    "SP500": "^GSPC",
    "NASDAQ": "^IXIC",
    "N225": "^N225",
    "VIX": "^VIX",
    "US10Y": "^TNX",
    "WTI": "CL=F",
    "GOLD": "GC=F",
    "BTCUSD": "BTC-USD",
    "ETHUSD": "ETH-USD",
}

class PlanDataCollector:
    def __init__(self):
        pass

    def calc_rsi(self, series: pd.Series, window: int = 14) -> pd.Series:
        """RSIのpandas実装"""
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window).mean()
        avg_loss = loss.rolling(window).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def fetch_multi_assets(self, start: str, end: str, interval: str = "1d", symbols: Optional[dict] = None) -> pd.DataFrame:
        if symbols is None:
            symbols = ASSET_SYMBOLS
        dfs = []
        for key, ticker in symbols.items():
            df = yf.download(ticker, start=start, end=end, interval=interval, progress=False)
            if df.empty:
                print(f"[collector] {ticker} のデータなし")
                continue
            df = df.reset_index()
            # 終値と出来高
            cols = ["Date", "Close"]
            if "Volume" in df.columns:
                cols.append("Volume")
            df = df[cols].rename(
                columns={"Close": f"{key}_Close", "Volume": f"{key}_Volume"}
            )
            if "Date" not in df.columns:
                df.rename(columns={"index": "Date"}, inplace=True)
            dfs.append(df)
        # 日付でマージ
        merged = None
        for df in dfs:
            if merged is None:
                merged = df
            else:
                merged = pd.merge(merged, df, on="Date", how="outer")
        if merged is not None:
            merged = merged.sort_values("Date")
            merged = merged.fillna(method="ffill")
            merged = merged.dropna(subset=[f"USDJPY_Close"])  # 主要アセットで揃え
            merged = merged.reset_index(drop=True)
            # --- 特徴量計算 ---
            for key in symbols:
                c = f"{key}_Close"
                v = f"{key}_Volume"
                # --- リターン・ボラ ---
                if c in merged.columns:
                    merged[f"{key}_Return"] = merged[c].pct_change()
                    merged[f"{key}_Volatility_5d"] = merged[f"{key}_Return"].rolling(5).std()
                    merged[f"{key}_Volatility_20d"] = merged[f"{key}_Return"].rolling(20).std()
                    # --- RSI ---
                    merged[f"{key}_RSI_14d"] = self.calc_rsi(merged[c], window=14)
                    # --- ゴールデンクロス（短期5日と長期25日） ---
                    ma_short = merged[c].rolling(5).mean()
                    ma_long = merged[c].rolling(25).mean()
                    gc_flag = (ma_short > ma_long) & (ma_short.shift(1) <= ma_long.shift(1))
                    merged[f"{key}_GC_Flag"] = gc_flag.astype(int)
                    # --- 3本MA: パーフェクトオーダー ---
                    ma_mid = merged[c].rolling(25).mean()
                    ma_longer = merged[c].rolling(75).mean()
                    merged[f"{key}_MA5"] = ma_short
                    merged[f"{key}_MA25"] = ma_mid
                    merged[f"{key}_MA75"] = ma_longer
                    po_up = ((ma_short > ma_mid) & (ma_mid > ma_longer)).astype(int)
                    po_down = ((ma_short < ma_mid) & (ma_mid < ma_longer)).astype(int)
                    merged[f"{key}_PO_UP"] = po_up
                    merged[f"{key}_PO_DOWN"] = po_down
                # --- 出来高関連 ---
                if v in merged.columns:
                    merged[f"{key}_Volume_MA5"] = merged[v].rolling(5).mean()
                    merged[f"{key}_Volume_MA20"] = merged[v].rolling(20).mean()
                    # --- 出来高急増フラグ（20日MAの2倍超でフラグ） ---
                    avg20 = merged[f"{key}_Volume_MA20"]
                    merged[f"{key}_Volume_Spike"] = ((merged[v] > avg20 * 2) & (avg20 > 0)).astype(int)
        return merged

    def collect_all(self, lookback_days: int = 365) -> pd.DataFrame:
        end = datetime.today()
        start = end - timedelta(days=lookback_days)
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")
        df = self.fetch_multi_assets(start=start_str, end=end_str)
        return df

# --- テスト実行例 ---
if __name__ == "__main__":
    collector = PlanDataCollector()
    df = collector.collect_all(lookback_days=180)
    # 主要な特徴量を10日分出力サンプル
    print(df[[
        "Date",
        "USDJPY_Close", "USDJPY_RSI_14d", "USDJPY_GC_Flag", "USDJPY_PO_UP", "USDJPY_PO_DOWN", "USDJPY_Volume_Spike",
        "SP500_Close", "SP500_RSI_14d", "SP500_GC_Flag", "SP500_PO_UP", "SP500_PO_DOWN", "SP500_Volume_Spike"
    ]].tail(10))
