# src/plan_data/collector.py

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict

try:
    import yfinance as yf
except ImportError:
    raise ImportError("yfinance が必要です: pip install yfinance")

ASSET_SYMBOLS = {
    "USDJPY": "JPY=X",
    "SP500": "^GSPC",
    "N225": "^N225",
    "VIX": "^VIX",
    "BTCUSD": "BTC-USD",
}

class PlanDataCollector:
    def __init__(self):
        pass

    def fetch_multi_assets(
        self, start: str, end: str, interval: str = "1d", symbols: Optional[Dict] = None
    ) -> pd.DataFrame:
        if symbols is None:
            symbols = ASSET_SYMBOLS
        dfs = []
        for key, ticker in symbols.items():
            df = yf.download(ticker, start=start, end=end, interval=interval, progress=False)
            if df.empty:
                print(f"[collector] {ticker} のデータなし")
                continue
            df = df.reset_index()
            cols = ["Date", "Close"]
            if "Volume" in df.columns:
                cols.append("Volume")
            df = df[cols].rename(
                columns={"Close": f"{key}_Close", "Volume": f"{key}_Volume"}
            )
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
        return merged

    def collect_all(self, lookback_days: int = 365) -> pd.DataFrame:
        end = datetime.today()
        start = end - timedelta(days=lookback_days)
        df = self.fetch_multi_assets(
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d")
        )
        return df

# テスト実行例
if __name__ == "__main__":
    collector = PlanDataCollector()
    df = collector.collect_all(lookback_days=180)
    print(df.head())
