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
load_dotenv()

ASSET_SYMBOLS = {
    # --- 優先度S, A, Bアセット ---
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

class PlanDataCollector:
    def __init__(self, fred_api_key: Optional[str] = None, event_calendar_csv: Optional[str] = None):
        self.fred_api_key = fred_api_key or os.getenv("FRED_API_KEY")
        if not self.fred_api_key:
            print("[collector] ⚠️ FRED_API_KEYが未設定です")
        self.event_calendar_csv = event_calendar_csv or "data/market/event_calendar.csv"
        self.newsapi_key = os.getenv("NEWSAPI_KEY")
        if not self.newsapi_key:
            print("[collector] ⚠️ NEWSAPI_KEYが未設定です")

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

    def fetch_event_calendar(self) -> pd.DataFrame:
        """
        経済カレンダーCSV（カラム例: Date, FOMC, CPI, NFP, ...）
        """
        try:
            df = pd.read_csv(self.event_calendar_csv)
            df["Date"] = pd.to_datetime(df["Date"])
            return df
        except Exception as e:
            print(f"[collector] イベントカレンダー取得失敗: {e}")
            return pd.DataFrame()

    def fetch_newsapi_counts(self, start_date: str, end_date: str, query="usd jpy") -> pd.DataFrame:
        """
        NewsAPIで日次ニュース件数＋ポジ/ネガワード件数を返す
        """
        api_key = self.newsapi_key
        if not api_key:
            print("[collector] NEWSAPI_KEYが未設定です")
            return pd.DataFrame()
        dfs = []
        dt_start = datetime.strptime(start_date, "%Y-%m-%d")
        dt_end = datetime.strptime(end_date, "%Y-%m-%d")
        for d in pd.date_range(dt_start, dt_end):
            day_str = d.strftime("%Y-%m-%d")
            url = (
                f"https://newsapi.org/v2/everything?"
                f"q={query}&from={day_str}&to={day_str}&language=en&pageSize=100"
                f"&apiKey={api_key}"
            )
            try:
                r = requests.get(url, timeout=10)
                r.raise_for_status()
                data = r.json()
                n_total = data.get("totalResults", 0)
                articles = data.get("articles", [])
                # ポジ/ネガワード例（必要に応じて拡張）
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
                    {"Date": pd.to_datetime(day_str), "News_Count": n_total,
                     "News_Positive": pos_count, "News_Negative": neg_count}
                )
            except Exception as e:
                print(f"[collector] NewsAPI {day_str}取得失敗: {e}")
        if dfs:
            return pd.DataFrame(dfs)
        return pd.DataFrame()

    def collect_all(self, lookback_days: int = 365) -> pd.DataFrame:
        end = datetime.today()
        start = end - timedelta(days=lookback_days)
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")
        df = self.fetch_multi_assets(start=start_str, end=end_str)
        # FREDデータ
        for sid in FRED_SERIES.values():
            fred_df = self.fetch_fred_data(sid, start_str, end_str)
            if not fred_df.empty and df is not None:
                df = pd.merge(df, fred_df, on="Date", how="left")
                df = df.sort_values("Date").fillna(method="ffill")
        # イベントカレンダー
        event_df = self.fetch_event_calendar()
        if not event_df.empty and df is not None:
            df = pd.merge(df, event_df, on="Date", how="left")
        # NewsAPI（日次ニュース件数・ポジネガ件数）
        news_df = self.fetch_newsapi_counts(start_str, end_str)
        if not news_df.empty and df is not None:
            df = pd.merge(df, news_df, on="Date", how="left")
        if df is not None:
            df = df.reset_index(drop=True)
        return df

# --- テスト実行例 ---
if __name__ == "__main__":
    collector = PlanDataCollector()
    df = collector.collect_all(lookback_days=7)
    print(df[["Date", "News_Count", "News_Positive", "News_Negative"]].tail())
