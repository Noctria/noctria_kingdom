# src/plan_data/collector.py

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import os
import requests

try:
    import yfinance as yf
except ImportError:
    raise ImportError("yfinance が必要です: pip install yfinance")

from dotenv import load_dotenv
load_dotenv(dotenv_path="/mnt/d/noctria_kingdom/.env")

from plan_data.feature_spec import FEATURE_SPEC  # FEATURE_SPECはリスト

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

def align_to_feature_spec(df: pd.DataFrame) -> pd.DataFrame:
    """FEATURE_SPEC（リスト）に合わせて欠損列を補う・順序を揃える"""
    if df is None or df.empty:
        # 空のときでも仕様順の空DFを返す
        return pd.DataFrame(columns=FEATURE_SPEC)
    columns = FEATURE_SPEC
    for col in columns:
        if col not in df.columns:
            df[col] = pd.NA
    return df[columns]

def _ensure_date_column(df: pd.DataFrame) -> pd.DataFrame:
    """さまざまな形の 'Date' / index を 'date' 列(datetime64) に統一"""
    if df is None or df.empty:
        return df

    # すでに 'date' 列があるならOK
    if "date" in df.columns:
        pass
    # 'Date' 列があるなら小文字へ
    elif "Date" in df.columns:
        df = df.rename(columns={"Date": "date"})
    # index名がDate/dateのとき
    elif getattr(df.index, "name", None) in ("Date", "date"):
        df = df.reset_index().rename(columns={df.index.name: "date"})
    # DatetimeIndexだが名前が無いとき
    elif isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index().rename(columns={"index": "date"})
    else:
        # 最後の手段：もし 'Datetime' のような列名があるなら拾う
        for cand in ["datetime", "time", "timestamp"]:
            if cand in df.columns:
                df = df.rename(columns={cand: "date"})
                break

    # 型をdatetimeへ
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    return df

class PlanDataCollector:
    def __init__(self, fred_api_key: Optional[str] = None, event_calendar_csv: Optional[str] = None):
        self.fred_api_key = fred_api_key or os.getenv("FRED_API_KEY")
        if not self.fred_api_key:
            print("[collector] ⚠️ FRED_API_KEYが未設定です")
        self.event_calendar_csv = event_calendar_csv or "data/market/event_calendar.csv"
        self.newsapi_key = os.getenv("NEWSAPI_KEY")
        if not self.newsapi_key:
            print("[collector] ⚠️ NEWSAPI_KEYが未設定です")

    def fetch_multi_assets(
        self,
        start: str,
        end: str,
        interval: str = "1d",
        symbols: Optional[Dict[str, str]] = None
    ) -> pd.DataFrame:
        if symbols is None:
            symbols = ASSET_SYMBOLS

        dfs: List[pd.DataFrame] = []
        for key, ticker in symbols.items():
            try:
                df = yf.download(
                    ticker,
                    start=start,
                    end=end,
                    interval=interval,
                    progress=False,
                )
                if df is None or df.empty:
                    print(f"[collector] {ticker} のデータなし")
                    continue

                # indexが日付なので列化して 'date' に統一
                df = df.reset_index()
                df = _ensure_date_column(df)

                # yfinanceは 'Close' / 'Volume' が基本
                cols = [c for c in ["date", "Close", "Volume"] if c in df.columns]
                if "date" not in cols or "Close" not in df.columns:
                    # 想定外フォーマットはスキップ（ここで落ちないため）
                    print(f"[collector] {ticker} 形式想定外のためスキップ: cols={df.columns.tolist()}")
                    continue

                out = df[cols].copy()
                out = out.rename(
                    columns={
                        "Close": f"{key.lower()}_close",
                        "Volume": f"{key.lower()}_volume",
                    }
                )
                # 数値化（object/strを落とす）
                for c in out.columns:
                    if c != "date":
                        out[c] = pd.to_numeric(out[c], errors="coerce")
                dfs.append(out)

            except Exception as e:
                print(f"[collector] {ticker} の取得中エラー: {e}")

        if not dfs:
            # 何も取れなかった場合は空DF
            return pd.DataFrame(columns=["date"])

        # 外部結合で時系列を統一
        merged = dfs[0]
        for i in range(1, len(dfs)):
            merged = pd.merge(merged, dfs[i], on="date", how="outer")

        # 念のため 'date' 復元＆datetime化
        merged = _ensure_date_column(merged)

        # 'date' 列が無い場合でも落ちないように重複除去
        if "date" in merged.columns:
            merged = merged.sort_values("date").drop_duplicates(subset=["date"]).reset_index(drop=True)
        else:
            print("[collector] WARNING: 'date' 列が見つかりません。全列で重複排除を実施。")
            merged = merged.drop_duplicates().reset_index(drop=True)

        # 前方埋め
        merged = merged.sort_values("date").fillna(method="ffill")

        # usdjpy_close が無ければ警告だけ出して続行（以前はdropnaしていた）
        if "usdjpy_close" not in merged.columns:
            print("DEBUG: usdjpy_close はカラムに存在しません。続行します。")

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
            df = _ensure_date_column(df)
            df[f"{series_id.lower()}_value"] = pd.to_numeric(df[f"{series_id.lower()}_value"], errors="coerce")
            return df[["date", f"{series_id.lower()}_value"]]
        except Exception as e:
            print(f"[collector] FREDデータ({series_id})取得失敗: {e}")
            return pd.DataFrame()

    def fetch_event_calendar(self) -> pd.DataFrame:
        """経済カレンダーCSV（カラム例: date, fomc, cpi, nfp, ...）"""
        try:
            df = pd.read_csv(self.event_calendar_csv)
            df.columns = [col.lower() for col in df.columns]
            df = _ensure_date_column(df)
            return df
        except Exception as e:
            print(f"[collector] イベントカレンダー取得失敗: {e}")
            return pd.DataFrame()

    def fetch_newsapi_counts(self, start_date: str, end_date: str, query="usd jpy") -> pd.DataFrame:
        """NewsAPIで日次ニュース件数＋ポジ/ネガワード件数を返す（未設定ならスキップ）"""
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
                    {
                        "date": pd.to_datetime(day_str),
                        "news_count": n_total,
                        "news_positive": pos_count,
                        "news_negative": neg_count,
                    }
                )
            except Exception as e:
                print(f"[collector] NewsAPI {day_str}取得失敗: {e}")
        if dfs:
            out = pd.DataFrame(dfs)
            out = _ensure_date_column(out)
            return out
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
            if not fred_df.empty and df is not None and not df.empty:
                df = pd.merge(df, fred_df, on="date", how="left")
                df = df.sort_values("date").fillna(method="ffill")

        # イベントカレンダー
        event_df = self.fetch_event_calendar()
        if not event_df.empty and df is not None and not df.empty:
            df = pd.merge(df, event_df, on="date", how="left")

        # NewsAPI（日次ニュース件数・ポジネガ件数）
        news_df = self.fetch_newsapi_counts(start_str, end_str)
        if not news_df.empty and df is not None and not df.empty:
            df = pd.merge(df, news_df, on="date", how="left")

        if df is not None:
            df = _ensure_date_column(df)
            df = df.reset_index(drop=True)
            df = align_to_feature_spec(df)  # ★ ここで標準仕様に整形
        return df

# --- テスト実行例 ---
if __name__ == "__main__":
    collector = PlanDataCollector()
    df = collector.collect_all(lookback_days=7)
    print(df.head())
    # テスト時はfeature_specにあるカラム名でアクセス
    print(df[[col for col in df.columns if "news" in col or "date" in col]].tail())
