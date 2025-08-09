# src/plan_data/collector.py

import os
import time
from datetime import datetime, timedelta
from typing import Optional, Dict
from urllib.parse import urlencode

import pandas as pd
import requests

try:
    import yfinance as yf
except ImportError:
    raise ImportError("yfinance が必要です: pip install yfinance")

from dotenv import load_dotenv

# .env 読み込み（パスは環境に合わせて）
load_dotenv(dotenv_path="/mnt/d/noctria_kingdom/.env")

# FEATURE_SPEC はリスト（標準カラム順）。snake_case で運用想定。
from plan_data.feature_spec import FEATURE_SPEC  # noqa: E402


ASSET_SYMBOLS: Dict[str, str] = {
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

FRED_SERIES: Dict[str, str] = {
    "UNRATE": "UNRATE",
    "FEDFUNDS": "FEDFUNDS",
    "CPI": "CPIAUCSL",
}


def align_to_feature_spec(df: pd.DataFrame) -> pd.DataFrame:
    columns = FEATURE_SPEC
    for col in columns:
        if col not in df.columns:
            df[col] = pd.NA
    return df[columns]


class PlanDataCollector:
    def __init__(self, fred_api_key: Optional[str] = None, event_calendar_csv: Optional[str] = None):
        self.fred_api_key = fred_api_key or os.getenv("FRED_API_KEY")
        if not self.fred_api_key:
            print("[collector] ⚠️ FRED_API_KEYが未設定です")
        self.event_calendar_csv = event_calendar_csv or "data/market/event_calendar.csv"

        # 🔁 NewsAPI → GNews へ切替
        self.gnews_key = os.getenv("GNEWS_API_KEY")
        if not self.gnews_key:
            print("[collector] ⚠️ GNEWS_API_KEYが未設定です")

        # 任意調整用（環境変数で上書き可）
        self.gnews_page_size = int(os.getenv("GNEWS_PAGE_SIZE", "50"))   # 1リクエストあたり件数（最大100）
        self.gnews_max_pages = int(os.getenv("GNEWS_MAX_PAGES", "3"))    # 最大ページ数（リク制限回避用）
        self.gnews_retry = int(os.getenv("GNEWS_RETRY", "2"))            # 429 等のリトライ回数
        self.gnews_backoff = float(os.getenv("GNEWS_BACKOFF", "1.5"))    # バックオフ係数

    # --------- ヘルパ群 ---------

    @staticmethod
    def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
        cols = df.columns
        if isinstance(cols, pd.MultiIndex):
            df = df.copy()
            df.columns = ["_".join([str(c) for c in tup if c is not None and c != ""])
                          for tup in cols]
            return df
        if any(not isinstance(c, str) for c in cols):
            df = df.copy()
            df.columns = [str(c) for c in cols]
        return df

    @staticmethod
    def _ensure_date_column(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        candidates = ["date", "Date", "Datetime", "datetime"]
        found = None
        for c in candidates:
            if c in df.columns:
                found = c
                break
        if found is None:
            return df
        if found != "date":
            df = df.rename(columns={found: "date"})
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df

    @staticmethod
    def _pick_first_matching(df: pd.DataFrame, starts_with: str) -> Optional[str]:
        if starts_with in df.columns:
            return starts_with
        low = starts_with.lower()
        for c in df.columns:
            if c.lower().startswith(low):
                return c
        return None

    # --------- データ取得 ---------

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
                    ticker,
                    start=start,
                    end=end,
                    interval=interval,
                    progress=False,
                )
                if df is None or df.empty:
                    print(f"[collector] {ticker} のデータなし")
                    continue

                df = df.reset_index()
                df = self._flatten_columns(df)
                df = self._ensure_date_column(df)

                close_col = self._pick_first_matching(df, "Close")
                volume_col = self._pick_first_matching(df, "Volume")

                if close_col is None:
                    print(f"[collector] {ticker} の Close 列が見つからずスキップ: cols={df.columns.tolist()}")
                    continue

                out_cols = ["date", close_col]
                if volume_col is not None:
                    out_cols.append(volume_col)

                out = df[out_cols].copy().rename(
                    columns={
                        close_col: f"{key.lower()}_close",
                        **({volume_col: f"{key.lower()}_volume"} if volume_col else {}),
                    }
                )

                for c in out.columns:
                    if c != "date":
                        out[c] = pd.to_numeric(out[c], errors="coerce")

                dfs.append(out)

            except Exception as e:
                print(f"[collector] {ticker} の取得中エラー: {e}")

        if not dfs:
            return pd.DataFrame(columns=["date"])

        merged = dfs[0]
        for i in range(1, len(dfs)):
            merged = pd.merge(merged, dfs[i], on="date", how="outer")
            merged = self._ensure_date_column(merged)

        merged = self._ensure_date_column(merged)
        merged = self._flatten_columns(merged)

        if "date" in merged.columns:
            merged = merged.sort_values("date")
            merged = merged.drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)
        else:
            print("[collector] WARNING: 'date' 列が見つかりません。全列で重複排除を実施。")
            merged = merged.drop_duplicates().reset_index(drop=True)

        merged = merged.ffill()

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
            obs = r.json().get("observations", [])
            if not obs:
                return pd.DataFrame()
            df = pd.DataFrame(obs)
            df = df.rename(columns={"date": "date", "value": f"{series_id.lower()}_value"})
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
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
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
            return df
        except Exception as e:
            print(f"[collector] イベントカレンダー取得失敗: {e}")
            return pd.DataFrame()

    # ===== GNews: 期間まとめ取得→日付集計（レート制限対応） =====
    def fetch_gnews_counts(
        self,
        start_date: str,
        end_date: str,
        query: str = '(USD AND JPY) OR ("dollar" AND "yen") OR USDJPY',
        lang: str = "en",
    ) -> pd.DataFrame:
        """
        GNews v4 /search を期間まとめて取得し、publishedAt の日付で groupby 集計。
        レート制限を避けるためにページ数上限・指数バックオフ・リトライを実装。
        返却列: [date, news_count, news_positive, news_negative]
        """
        if not self.gnews_key:
            print("[collector] GNEWS_API_KEYが未設定です")
            return pd.DataFrame()

        base_url = "https://gnews.io/api/v4/search"
        page_size = max(1, min(100, self.gnews_page_size))
        max_pages = max(1, self.gnews_max_pages)

        params_common = {
            "q": query,
            "from": start_date,
            "to": end_date,
            "lang": lang,
            "max": page_size,
            "sortby": "publishedAt",
            "token": self.gnews_key,
        }

        articles_all = []
        page = 1
        retries = self.gnews_retry

        while page <= max_pages:
            params = {**params_common, "page": page}
            url = base_url + "?" + urlencode(params)

            try:
                r = requests.get(url, timeout=10)
                if r.status_code == 429:
                    if retries > 0:
                        wait = (self.gnews_backoff ** (self.gnews_retry - retries)) * 2.0
                        print(f"[collector] GNews 429: wait {wait:.1f}s & retry... (page={page})")
                        time.sleep(wait)
                        retries -= 1
                        continue
                    else:
                        print("[collector] GNews 429: リトライ上限。部分結果で続行します。")
                        break

                r.raise_for_status()
                data = r.json()
                articles = data.get("articles", [])
                if not articles:
                    break

                articles_all.extend(articles)

                # ページング終了条件
                if len(articles) < page_size:
                    break

                # 次ページへ
                page += 1
                # 軽いレート間隔（サーバー負荷軽減）
                time.sleep(0.4)

            except requests.RequestException as e:
                print(f"[collector] GNews取得失敗(page={page}): {e}")
                # 致命的でなければ部分結果で続行
                break

        if not articles_all:
            return pd.DataFrame()

        # 簡易スコアリング
        pos_words = ["gain", "rise", "surge", "record high", "bull", "up", "strong", "beat"]
        neg_words = ["fall", "drop", "crash", "bear", "loss", "down", "weak", "miss"]

        rows = []
        for a in articles_all:
            title = (a.get("title") or "")
            desc = (a.get("description") or "")
            text = (title + " " + desc).lower()

            pub = a.get("publishedAt") or ""
            try:
                # publishedAt: ISO8601 (e.g. 2024-01-01T12:34:56Z)
                d = pd.to_datetime(pub, errors="coerce").date()
            except Exception:
                d = None

            if d is None:
                continue

            rows.append({
                "date": pd.to_datetime(str(d)),
                "pos": int(any(w in text for w in pos_words)),
                "neg": int(any(w in text for w in neg_words)),
                "cnt": 1
            })

        if not rows:
            return pd.DataFrame()

        tmp = pd.DataFrame(rows)
        agg = tmp.groupby("date").agg(
            news_count=("cnt", "sum"),
            news_positive=("pos", "sum"),
            news_negative=("neg", "sum"),
        ).reset_index()

        return agg

    def collect_all(self, lookback_days: int = 365) -> pd.DataFrame:
        end = datetime.today()
        start = end - timedelta(days=lookback_days)
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")

        # マーケット価格群
        df = self.fetch_multi_assets(start=start_str, end=end_str)

        # FRED（CPI/失業率/FF金利など）
        for sid in FRED_SERIES.values():
            fred_df = self.fetch_fred_data(sid, start_str, end_str)
            if not fred_df.empty and df is not None and not df.empty:
                df = pd.merge(df, fred_df, on="date", how="left")
                df = df.sort_values("date").ffill()

        # 経済カレンダー
        event_df = self.fetch_event_calendar()
        if not event_df.empty and df is not None and not df.empty:
            df = pd.merge(df, event_df, on="date", how="left")

        # 🔁 GNews（日次ニュース件数・ポジネガ件数）
        news_df = self.fetch_gnews_counts(start_str, end_str)
        if not news_df.empty:
            if df is None or df.empty:
                df = news_df.copy()
            else:
                df = pd.merge(df, news_df, on="date", how="left")

        if df is not None:
            df = df.reset_index(drop=True)
            df = align_to_feature_spec(df)

        return df


# --- テスト実行例 ---
if __name__ == "__main__":
    collector = PlanDataCollector()
    df = collector.collect_all(lookback_days=30)
    cols = [c for c in df.columns if "news" in c or c == "date"]
    print(df[cols].tail())
