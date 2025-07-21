import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict
import os
import requests

try:
    import yfinance as yf
except ImportError:
    raise ImportError("yfinance が必要です: pip install yfinance")

from dotenv import load_dotenv
load_dotenv()

ASSET_SYMBOLS = {
    "USDJPY": "JPY=X",
    "SP500": "^GSPC",
    "N225": "^N225",
    "VIX": "^VIX",
    "BTCUSD": "BTC-USD",
    "US10Y": "^TNX",
    "DXY": "DX-Y.NYB",
    "GDAXI": "^GDAXI",
    "FTSE": "^FTSE",
    "EURJPY": "EURJPY=X",
    "EURUSD": "EURUSD=X",
    "AUDJPY": "AUDJPY=X",
    "GBPUSD": "GBPUSD=X",
    "GOLD": "GC=F",
    "WTI": "CL=F",
    "MOVE": "^MOVE",
    # 優先度A：仮想通貨
    "ETHUSD": "ETH-USD",
    "XRPUSD": "XRP-USD",
    "SOLUSD": "SOL-USD",
    "DOGEUSD": "DOGE-USD",
}

FRED_SERIES = {
    "UNRATE": "UNRATE",         # 失業率
    "FEDFUNDS": "FEDFUNDS",     # 政策金利
    "CPI": "CPIAUCSL",          # CPI（米消費者物価）
}

class PlanDataCollector:
    def __init__(self, fred_api_key: Optional[str] = None):
        self.fred_api_key = fred_api_key or os.getenv("FRED_API_KEY")
        if not self.fred_api_key:
            print("[collector] ⚠️ FRED_API_KEYが未設定です")

    def fetch_multi_assets(
        self, start: str, end: str, interval: str = "1d", symbols: Optional[Dict] = None
    ) -> pd.DataFrame:
        if symbols is None:
            symbols = ASSET_SYMBOLS
        dfs = []
        for key, ticker in symbols.items():
            try:
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
            except Exception as e:
                print(f"[collector] {ticker} の取得中エラー: {e}")
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
            merged = merged.dropna(subset=[f"USDJPY_Close"])
            merged = merged.reset_index(drop=True)
        return merged

    def fetch_fred_data(self, series_id: str, start_date: str, end_date: str) -> pd.DataFrame:
        if not self.fred_api_key:
            print("[collector] ⚠️ FRED_API_KEY未設定。FREDデータをスキップ")
            return pd.DataFrame()
        url = "https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": series_id,
            "api_key": self.fred_api_key,
            "file_type": "json",
            "observation_start": start_date,
            "observation_end": end_date,
        }
        try:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            obs = r.json()["observations"]
            df = pd.DataFrame(obs)
            df = df.rename(columns={"date": "Date", "value": f"{series_id}_Value"})
            df["Date"] = pd.to_datetime(df["Date"])
            df[f"{series_id}_Value"] = pd.to_numeric(df[f"{series_id}_Value"], errors="coerce")
            return df[["Date", f"{series_id}_Value"]]
        except Exception as e:
            print(f"[collector] FREDデータ({series_id})取得失敗: {e}")
            return pd.DataFrame()

    def collect_all(self, lookback_days: int = 365) -> pd.DataFrame:
        end = datetime.today()
        start = end - timedelta(days=lookback_days)
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")
        df = self.fetch_multi_assets(start=start_str, end=end_str)
        # FREDデータを統合
        for sid in FRED_SERIES.values():
            fred_df = self.fetch_fred_data(sid, start_str, end_str)
            if not fred_df.empty and df is not None:
                df = pd.merge(df, fred_df, on="Date", how="left")
                df = df.sort_values("Date").fillna(method="ffill")
        if df is not None:
            df = df.reset_index(drop=True)
        return df

# --- テスト実行例 ---
if __name__ == "__main__":
    collector = PlanDataCollector()
    df = collector.collect_all(lookback_days=180)
    print(df.tail())
    # "UNRATE_Value", "FEDFUNDS_Value", "CPIAUCSL_Value" などが付加されていることを確認
