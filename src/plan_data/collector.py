# src/plan_data/collector.py

import os
from datetime import datetime, timedelta
from typing import Optional, Dict

import pandas as pd
import requests

try:
    import yfinance as yf
except ImportError:
    raise ImportError("yfinance が必要です: pip install yfinance")

from dotenv import load_dotenv

# .env をロード（パスは環境に合わせて）
load_dotenv(dotenv_path="/mnt/d/noctria_kingdom/.env")

# =====================================================
# 取得するマーケットシンボル（キー名=出力カラムの接頭辞）
# =====================================================
ASSET_SYMBOLS: Dict[str, str] = {
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

# FRED シリーズ（出力はすべて *_value の snake_case）
FRED_SERIES = {
    "UNRATE": "UNRATE",       # 失業率
    "FEDFUNDS": "FEDFUNDS",   # 政策金利
    "CPI": "CPIAUCSL",        # CPI
}


def _ensure_datetime_series(s: pd.Series) -> pd.Series:
    """pandas の日時列を安全に変換（tz情報は落として日付だけに寄せやすく）"""
    s = pd.to_datetime(s, errors="coerce", utc=False)
    return s


def _numericify(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    """指定列を to_numeric で数値化（errors='coerce'）"""
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


class PlanDataCollector:
    def __init__(
        self,
        fred_api_key: Optional[str] = None,
        event_calendar_csv: Optional[str] = None,
    ):
        self.fred_api_key = fred_api_key or os.getenv("FRED_API_KEY")
        if not self.fred_api_key:
            print("[collector] ⚠️ FRED_API_KEYが未設定です")

        self.newsapi_key = os.getenv("NEWSAPI_KEY")
        if not self.newsapi_key:
            print("[collector] ⚠️ NEWSAPI_KEYが未設定です")

        # 経済カレンダー（任意）
        self.event_calendar_csv = event_calendar_csv or "data/market/event_calendar.csv"

    # -------------------------------------------------
    # マーケットデータ（Yahoo Finance）
    # -------------------------------------------------
    def fetch_multi_assets(
        self,
        start: str,
        end: str,
        interval: str = "1d",
        symbols: Optional[Dict[str, str]] = None,
    ) -> pd.DataFrame:
        if symbols is None:
            symbols = ASSET_SYMBOLS

        dfs = []
        for key, ticker in symbols.items():
            try:
                df = yf.download(
                    ticker, start=start, end=end, interval=interval, progress=False
                )
                if df is None or df.empty:
                    print(f"[collector] {ticker} のデータなし")
                    continue

                df = df.reset_index()
                # 必要カラム抽出
                cols = ["Date", "Close"]
                if "Volume" in df.columns:
                    cols.append("Volume")
                df = df[cols]

                # rename -> snake_case
                base = key.lower()
                rename_map = {
                    "Date": "date",
                    "Close": f"{base}_close",
                }
                if "Volume" in cols:
                    rename_map["Volume"] = f"{base}_volume"
                df = df.rename(columns=rename_map)

                # 型整形
                df["date"] = _ensure_datetime_series(df["date"])
                num_cols = [c for c in df.columns if c != "date"]
                df = _numericify(df, num_cols)

                dfs.append(df)
            except Exception as e:
                print(f"[collector] {ticker} の取得中エラー: {e}")

        if not dfs:
            return pd.DataFrame()

        # 日付で順次マージ
        merged = dfs[0]
        for i in range(1, len(dfs)):
            merged = pd.merge(merged, dfs[i], on="date", how="outer")

        # クレンジング
        merged = merged.sort_values("date")
        merged = merged.ffill()
        merged = merged.drop_duplicates(subset=["date"]).reset_index(drop=True)

        # usdjpy_close が取れていないと下流が空振りするので早期に気づけるよう警告
        if "usdjpy_close" not in merged.columns:
            print("DEBUG: usdjpy_close が存在しません（USDJPYのダウンロード失敗の可能性）。")

        return merged

    # -------------------------------------------------
    # FRED（任意）
    # -------------------------------------------------
    def fetch_fred_data(self, series_id: str, start_date: str, end_date: str) -> pd.DataFrame:
        if not self.fred_api_key:
            # 既に初期化時に警告は出しているので静かにスキップ
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
            obs = r.json().get("observations", [])
            if not obs:
                return pd.DataFrame()

            df = pd.DataFrame(obs)
            df = df.rename(columns={"date": "date", "value": f"{series_id.lower()}_value"})
            df["date"] = _ensure_datetime_series(df["date"])
            df[f"{series_id.lower()}_value"] = pd.to_numeric(df[f"{series_id.lower()}_value"], errors="coerce")

            # 日付ごとに最新観測のみ（重複除去）
            df = df[["date", f"{series_id.lower()}_value"]].drop_duplicates(subset=["date"])
            return df
        except Exception as e:
            print(f"[collector] FREDデータ({series_id})取得失敗: {e}")
            return pd.DataFrame()

    # -------------------------------------------------
    # 経済カレンダー（任意のCSV）
    # -------------------------------------------------
    def fetch_event_calendar(self) -> pd.DataFrame:
        try:
            df = pd.read_csv(self.event_calendar_csv)
        except Exception as e:
            print(f"[collector] イベントカレンダー取得失敗: {e}")
            return pd.DataFrame()

        # カラム名を snake_case に（最低限 date は必須）
        df.columns = [str(c).strip().lower() for c in df.columns]
        if "date" not in df.columns:
            print("[collector] 経済カレンダーCSVに 'date' 列がありません。スキップします。")
            return pd.DataFrame()

        df["date"] = _ensure_datetime_series(df["date"])
        # 0/1/True/False を int に寄せる（イベントフラグ扱い想定）
        for c in df.columns:
            if c == "date":
                continue
            if df[c].dropna().isin([0, 1, True, False]).all():
                df[c] = df[c].astype("Int64")

        df = df.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
        return df

    # -------------------------------------------------
    # NewsAPI（任意）— キー未設定なら何もしない
    # -------------------------------------------------
    def fetch_newsapi_counts(self, start_date: str, end_date: str, query: str = "usd jpy") -> pd.DataFrame:
        api_key = self.newsapi_key
        if not api_key:
            # 明示的にスキップ
            return pd.DataFrame()

        dt_start = datetime.strptime(start_date, "%Y-%m-%d")
        dt_end = datetime.strptime(end_date, "%Y-%m-%d")

        rows = []
        for d in pd.date_range(dt_start, dt_end):
            day_str = d.strftime("%Y-%m-%d")
            url = (
                "https://newsapi.org/v2/everything?"
                f"q={query}&from={day_str}&to={day_str}&language=en&pageSize=100"
                f"&apiKey={api_key}"
            )
            try:
                r = requests.get(url, timeout=10)
                r.raise_for_status()
                data = r.json() or {}
                n_total = data.get("totalResults", 0)
                articles = data.get("articles", []) or []

                pos_words = ["gain", "rise", "surge", "record high", "bull", "up"]
                neg_words = ["fall", "drop", "crash", "bear", "loss", "down"]

                def _count(words):
                    cnt = 0
                    for a in articles:
                        t = (a.get("title") or "").lower()
                        if any(w in t for w in words):
                            cnt += 1
                    return cnt

                rows.append(
                    {
                        "date": pd.to_datetime(day_str),
                        "news_count": int(n_total) if isinstance(n_total, int) else 0,
                        "news_positive": _count(pos_words),
                        "news_negative": _count(neg_words),
                    }
                )
            except Exception as e:
                print(f"[collector] NewsAPI {day_str}取得失敗: {e}")

        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows).drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
        return df

    # -------------------------------------------------
    # すべて集約
    # -------------------------------------------------
    def collect_all(self, lookback_days: int = 365) -> pd.DataFrame:
        end_dt = datetime.today()
        start_dt = end_dt - timedelta(days=lookback_days)
        start_str = start_dt.strftime("%Y-%m-%d")
        end_str = end_dt.strftime("%Y-%m-%d")

        # 1) マーケット
        df = self.fetch_multi_assets(start=start_str, end=end_str)

        if df is None or df.empty:
            print("[collector] ⚠️ マーケットデータが空です。以降の結合はスキップします。")
            return pd.DataFrame()

        # 2) FRED（任意・あれば left join）
        for sid in FRED_SERIES.values():
            fred_df = self.fetch_fred_data(sid, start_str, end_str)
            if not fred_df.empty:
                df = pd.merge(df, fred_df, on="date", how="left")
                df = df.sort_values("date").ffill()

        # 3) イベントカレンダー（任意）
        event_df = self.fetch_event_calendar()
        if not event_df.empty:
            df = pd.merge(df, event_df, on="date", how="left")

        # 4) NewsAPI（任意）
        news_df = self.fetch_newsapi_counts(start_str, end_str)
        if not news_df.empty:
            df = pd.merge(df, news_df, on="date", how="left")

        # 最終クレンジング
        df = df.sort_values("date").drop_duplicates(subset=["date"]).reset_index(drop=True)

        # 代表カラムの存在チェック（下流が使う想定の一部）
        for must in ["usdjpy_close", "sp500_close", "vix_close"]:
            if must not in df.columns:
                print(f"[collector] ⚠️ 代表カラムが欠落しています: {must}")

        return df


# --- テスト実行例 ---
if __name__ == "__main__":
    collector = PlanDataCollector()
    df = collector.collect_all(lookback_days=7)
    print("columns:", df.columns.tolist())
    print(df.tail())
