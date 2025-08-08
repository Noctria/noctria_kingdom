# src/plan_data/collector.py

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
load_dotenv(dotenv_path="/mnt/d/noctria_kingdom/.env")

from plan_data.feature_spec import FEATURE_SPEC

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
    "ETHUSD": "ETH-USD",
    "XRPUSD": "XRP-USD",
    "SOLUSD": "SOL-USD",
    "DOGEUSD": "DOGE-USD",
    "HSI": "^HSI",
    "SHANGHAI": "000001.SS",
    "KOSPI": "^KS11",
    "QQQ": "QQQ",
    "TLT": "TLT",
    "GLD": "GLD",
    "RUSSELL": "^RUT",
}

FRED_SERIES = {
    "UNRATE": "UNRATE",
    "FEDFUNDS": "FEDFUNDS",
    "CPI": "CPIAUCSL",
}

def align_to_feature_spec(df: pd.DataFrame) -> pd.DataFrame:
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

class PlanDataCollector:
    def __init__(self, fred_api_key: Optional[str] = None, event_calendar_csv: Optional[str] = None):
        self.fred_api_key = fred_api_key or os.getenv("FRED_API_KEY")
        if not self.fred_api_key:
            print("[collector] ⚠️ FRED_API_KEYが未設定です")
        self.event_calendar_csv = event_calendar_csv or "data/market/event_calendar.csv"
        self.newsapi_key = os.getenv("NEWSAPI_KEY")
        self.gnews_api_key = os.getenv("GNEWS_API_KEY")
        if not self.newsapi_key:
            print("[collector] ⚠️ NEWSAPI_KEYが未設定です")
        if not self.gnews_api_key:
            print("[collector] ⚠️ GNEWS_API_KEYが未設定です")

    def fetch_multi_assets(self, start: str, end: str, interval: str = "1d", symbols: Optional[Dict] = None) -> pd.DataFrame:
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
                    columns={
                        "Date": "date",
                        "Close": f"{key.lower()}_close",
                        "Volume": f"{key.lower()}_volume"
                    }
                )
                dfs.append(df)
            except Exception as e:
                print(f"[collector] {ticker} の取得中エラー: {e}")
        merged = None
        for df in dfs:
            if merged is None:
                merged = df
            else:
                merged = pd.merge(merged, df, on="date", how="outer")
        if merged is not None:
            merged = merged.sort_values("date")
            merged = merged.fillna(method="ffill")
            # MultiIndexをフラット化
            if isinstance(merged.columns, pd.MultiIndex):
                merged.columns = ['_'.join(filter(None, col)) for col in merged.columns]
            key = "usdjpy_close"
            if key in merged.columns:
                merged = merged.dropna(subset=[key])
            else:
                print(f"DEBUG: {key} はカラムに存在しません。dropnaをスキップします。")
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
            df = df.rename(columns={"date": "date", "value": f"{series_id.lower()}_value"})
            df["date"] = pd.to_datetime(df["date"])
            df[f"{series_id.lower()}_value"] = pd.to_numeric(df[f"{series_id.lower()}_value"], errors="coerce")
            return df[["date", f"{series_id.lower()}_value"]]
        except Exception as e:
            print(f"[collector] FREDデータ({series_id})取得失敗: {e}")
            return pd.DataFrame()

    def fetch_event_calendar(self) -> pd.DataFrame:
        try:
            df = pd.read_csv(self.event_calendar_csv)
            df.columns = [col.lower() for col in df.columns]
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
            return df
        except Exception as e:
            print(f"[collector] イベントカレンダー取得失敗: {e}")
            return pd.DataFrame()

    def fetch_gnews_counts(self, start_date: str, end_date: str, query="usd jpy") -> pd.DataFrame:
        if not self.gnews_api_key:
            print("[collector] GNEWS_API_KEYが未設定です")
            return pd.DataFrame()

        dfs = []
        dt_start = datetime.strptime(start_date, "%Y-%m-%d")
        dt_end = datetime.strptime(end_date, "%Y-%m-%d")

        for d in pd.date_range(dt_start, dt_end):
            day_str = d.strftime("%Y-%m-%d")
            url = (
                f"https://gnews.io/api/v4/search?"
                f"q={query}&from={day_str}&to={day_str}&lang=en&max=100&token={self.gnews_api_key}"
            )
            try:
                r = requests.get(url, timeout=10)
                r.raise_for_status()
                data = r.json()
                articles = data.get("articles", [])
                n_total = len(articles)
                pos_words = ["gain", "rise", "surge", "record high", "bull", "up"]
                neg_words = ["fall", "drop", "crash", "bear", "loss", "down"]
                pos_count = sum(
                    any(w in (a.get("title") or "").lower() for w in pos_words)
                    for a in articles
                )
                neg_count = sum(
                    any(w in (a.get("title") or "").lower() for w in neg_words)
                    for a in articles
                )
                dfs.append(
                    {"date": pd.to_datetime(day_str), "news_count": n_total,
                     "news_positive": pos_count, "news_negative": neg_count}
                )
            except Exception as e:
                print(f"[collector] GNews {day_str}取得失敗: {e}")

        if dfs:
            return pd.DataFrame(dfs)
        return pd.DataFrame()

    def collect_all(self, lookback_days: int = 365) -> pd.DataFrame:
        end = datetime.today()
        start = end - timedelta(days=lookback_days)
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")

        df = self.fetch_multi_assets(start=start_str, end=end_str)

        for sid in FRED_SERIES.values():
            fred_df = self.fetch_fred_data(sid, start_str, end_str)
            if not fred_df.empty and df is not None:
                df = pd.merge(df, fred_df, on="date", how="left")
                df = df.sort_values("date").fillna(method="ffill")

        event_df = self.fetch_event_calendar()
        if not event_df.empty and df is not None:
            df = pd.merge(df, event_df, on="date", how="left")

        news_df = self.fetch_gnews_counts(start_str, end_str)
        if not news_df.empty and df is not None:
            df = pd.merge(df, news_df, on="date", how="left")

        if df is not None:
            df = df.reset_index(drop=True)
            df = align_to_feature_spec(df)

        return df

# --- テスト実行例 ---
if __name__ == "__main__":
    collector = PlanDataCollector()
    df = collector.collect_all(lookback_days=7)
    print(df[[col for col in df.columns if "news" in col or "date" in col]].tail())
