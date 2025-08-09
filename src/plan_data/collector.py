# src/plan_data/collector.py

import os
import math
import time
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
import requests

try:
    import yfinance as yf
except ImportError:
    raise ImportError("yfinance が必要です: pip install yfinance")

from dotenv import load_dotenv
load_dotenv(dotenv_path="/mnt/d/noctria_kingdom/.env")

# FEATURE_SPEC はリスト（標準カラム順）。snake_case で運用。
from plan_data.feature_spec import FEATURE_SPEC


# =========================
# 定数
# =========================
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
    """FEATURE_SPEC（リスト）に合わせて不足カラムは追加（NaN）し、その順序で返す。"""
    columns = FEATURE_SPEC
    for col in columns:
        if col not in df.columns:
            df[col] = pd.NA
    return df[columns]


# =========================
# Collector
# =========================
class PlanDataCollector:
    def __init__(
        self,
        fred_api_key: Optional[str] = None,
        event_calendar_csv: Optional[str] = None,
        gnews_api_key: Optional[str] = None,
        cache_dir: Optional[Path] = None,
    ):
        # FRED
        self.fred_api_key = fred_api_key or os.getenv("FRED_API_KEY")
        if not self.fred_api_key:
            print("[collector] ⚠️ FRED_API_KEYが未設定です")

        # 経済カレンダー
        self.event_calendar_csv = event_calendar_csv or "data/market/event_calendar.csv"

        # GNews
        self.gnews_api_key = gnews_api_key or os.getenv("GNEWS_API_KEY")
        if not self.gnews_api_key:
            print("[collector] ⚠️ GNEWS_API_KEYが未設定です（ニュース特徴は0埋め/欠損になります）")

        # キャッシュ格納先
        self.cache_dir = Path(cache_dir or "data/cache")
        (self.cache_dir / "gnews").mkdir(parents=True, exist_ok=True)

        # GNews チューニング（.envで上書き可）
        self.gnews_page_size = int(os.getenv("GNEWS_PAGE_SIZE", "50"))      # 10〜100
        self.gnews_max_pages = int(os.getenv("GNEWS_MAX_PAGES", "2"))       # 1日最大ページ数
        self.gnews_retry = int(os.getenv("GNEWS_RETRY", "3"))               # リトライ回数
        self.gnews_backoff = float(os.getenv("GNEWS_BACKOFF", "1.5"))       # 指数バックオフ係数
        self.gnews_rate_per_min = int(os.getenv("GNEWS_RATE_PER_MIN", "12"))  # 1分あたり上限（無料: 約12程度）
        self._last_call_ts: List[float] = []  # レート制御用リングバッファ

        # セッション再利用
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "noctria-collector/1.0"})

    # ---------- ヘルパ ----------

    @staticmethod
    def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
        """yfinance の MultiIndex 列などをフラット化。"""
        cols = df.columns
        if isinstance(cols, pd.MultiIndex):
            df = df.copy()
            df.columns = ["_".join([str(c) for c in tup if c is not None and c != ""]) for tup in cols]
            return df
        if any(not isinstance(c, str) for c in cols):
            df = df.copy()
            df.columns = [str(c) for c in cols]
        return df

    @staticmethod
    def _ensure_date_column(df: pd.DataFrame) -> pd.DataFrame:
        """'date' 列を保証。存在しなければ 'Date' / 'Datetime' 等を探して変換。"""
        df = df.copy()
        candidates = ["date", "Date", "Datetime", "datetime", "index"]
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
        """'Close', 'Close_^GSPC', 'Close_JPY=X' のような列から前方一致で列名を返す。"""
        if starts_with in df.columns:
            return starts_with
        low = starts_with.lower()
        for c in df.columns:
            if c.lower().startswith(low):
                return c
        return None

    # ---------- yfinance ----------

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
                df = yf.download(ticker, start=start, end=end, interval=interval, progress=False)
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

                out_cols = ["date", close_col] + ([volume_col] if volume_col else [])
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

        # 価格系は前方補完（粒度差吸収）
        merged = merged.ffill()

        if "usdjpy_close" not in merged.columns:
            print("DEBUG: usdjpy_close はカラムに存在しません。続行します。")

        return merged

    # ---------- FRED ----------

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
            r = self._session.get(url, params=params, timeout=10)
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

    # ---------- 経済カレンダー ----------

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

    # ---------- GNews（最適化・キャッシュつき） ----------

    def _respect_rate_limit(self):
        """1分あたりのコール上限をだいたい守る（簡易実装）。"""
        if self.gnews_rate_per_min <= 0:
            return
        now = time.time()
        window = 60.0
        self._last_call_ts = [t for t in self._last_call_ts if now - t < window]
        if len(self._last_call_ts) >= self.gnews_rate_per_min:
            sleep_sec = window - (now - self._last_call_ts[0]) + 0.05
            if sleep_sec > 0:
                time.sleep(sleep_sec)
        self._last_call_ts.append(time.time())

    def _gnews_day_cache_path(self, day: datetime, query_key: str) -> Path:
        """
        日毎キャッシュのパス（query_keyはクエリをファイル名安全化したキー）。
        例: data/cache/gnews/2025-07-01_usdjpy.parquet
        """
        fname = f"{day.strftime('%Y-%m-%d')}_{query_key}.parquet"
        return self.cache_dir / "gnews" / fname

    def _read_day_cache(self, day: datetime, query_key: str) -> Optional[pd.DataFrame]:
        path = self._gnews_day_cache_path(day, query_key)
        if path.exists():
            try:
                return pd.read_parquet(path)
            except Exception:
                # 壊れていたら削除
                path.unlink(missing_ok=True)
        return None

    def _write_day_cache(self, day: datetime, query_key: str, df: pd.DataFrame) -> None:
        path = self._gnews_day_cache_path(day, query_key)
        try:
            df.to_parquet(path, index=False)
        except Exception:
            # 書き込み失敗は無視
            pass

    def _fetch_gnews_one_day(self, day: datetime, query: str, lang: str = "en") -> pd.DataFrame:
        """
        単一日のGNews結果をページング・リトライ付きで収集し、DataFrameで返す。
        出力列: date(news日), news_count, news_positive, news_negative
        """
        if not self.gnews_api_key:
            # APIキー無し → 0行
            return pd.DataFrame(columns=["date", "news_count", "news_positive", "news_negative"])

        # キャッシュ確認
        query_key = "".join(ch for ch in query.lower().replace(" ", "_") if ch.isalnum() or ch in "_-")
        cached = self._read_day_cache(day, query_key)
        if cached is not None:
            return cached

        # クエリ準備（GNewsの検索式はURLエンコード推奨）
        q = quote_plus(query)
        from_str = day.strftime("%Y-%m-%d")
        to_str = day.strftime("%Y-%m-%d")

        pos_words = ["gain", "rise", "surge", "record high", "bull", "up", "strong"]
        neg_words = ["fall", "drop", "crash", "bear", "loss", "down", "weak"]

        total_articles = 0
        pos_count = 0
        neg_count = 0

        # ページング（GNews: page/ max param）
        for page in range(1, self.gnews_max_pages + 1):
            # レート制御
            self._respect_rate_limit()

            url = (
                "https://gnews.io/api/v4/search"
                f"?q={q}"
                f"&from={from_str}"
                f"&to={to_str}"
                f"&lang={lang}"
                f"&max={self.gnews_page_size}"
                f"&page={page}"
                f"&sortby=publishedAt"
                f"&token={self.gnews_api_key}"
            )

            ok = False
            last_err = None
            for attempt in range(self.gnews_retry):
                try:
                    r = self._session.get(url, timeout=10)
                    # 429対策：短い待機＋指数バックオフ
                    if r.status_code == 429:
                        wait = (self.gnews_backoff ** attempt) + random.uniform(0, 0.25)
                        time.sleep(wait)
                        continue
                    r.raise_for_status()
                    data = r.json()
                    articles = data.get("articles", [])
                    if not articles:
                        ok = True
                        break

                    # 集計
                    total_articles += len(articles)
                    for a in articles:
                        title = (a.get("title") or "").lower()
                        if any(w in title for w in pos_words):
                            pos_count += 1
                        if any(w in title for w in neg_words):
                            neg_count += 1

                    # GNewsは最大 10*page ほどで頭打ちになることが多いので早期終了判定
                    if len(articles) < self.gnews_page_size:
                        ok = True
                        break

                    ok = True
                    # まだ記事が続きそうなら次ページへ
                    # ただし無料版レートの都合で深追いしすぎない
                except requests.HTTPError as e:
                    last_err = e
                    wait = (self.gnews_backoff ** attempt) + random.uniform(0, 0.25)
                    time.sleep(wait)
                except requests.RequestException as e:
                    last_err = e
                    wait = (self.gnews_backoff ** attempt) + random.uniform(0, 0.25)
                    time.sleep(wait)

            if not ok and last_err:
                print(f"[collector] GNews {from_str}取得失敗: {last_err}")
                # その日の分は諦める（0カウントで記録）
                break

            # 1ページで記事が尽きたらループ終了
            if ok and (total_articles == 0 or total_articles % self.gnews_page_size != 0):
                break

        out = pd.DataFrame(
            [{
                "date": pd.to_datetime(from_str),
                "news_count": float(total_articles),
                "news_positive": float(pos_count),
                "news_negative": float(neg_count),
            }]
        )
        # キャッシュ書き込み
        self._write_day_cache(day, query_key, out)
        return out

    def fetch_gnews_counts(
        self,
        start_date: str,
        end_date: str,
        query: str = '(USD AND JPY) OR ("dollar" AND "yen") OR USDJPY',
        lang: str = "en",
    ) -> pd.DataFrame:
        """
        GNewsで日次ニュース件数＋ポジ/ネガワード件数を返す（最適化版）
        - 日毎キャッシュ（Parquet）
        - レート制御・指数バックオフ
        - ページング
        """
        try:
            dt_start = datetime.strptime(start_date, "%Y-%m-%d")
            dt_end = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            # フォーマット不正時は空
            return pd.DataFrame()

        all_days: List[pd.DataFrame] = []
        day = dt_start
        while day <= dt_end:
            df_day = self._fetch_gnews_one_day(day, query=query, lang=lang)
            all_days.append(df_day)
            day += timedelta(days=1)

        if not all_days:
            return pd.DataFrame()

        df = pd.concat(all_days, ignore_index=True)
        # 念のため整形
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for c in ["news_count", "news_positive", "news_negative"]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

        # 比率などは FeatureEngineer 側で計算する想定だが、最低限の列はここで用意しておく
        return df[["date", "news_count", "news_positive", "news_negative"]].sort_values("date")

    # ---------- 収集一括 ----------

    def collect_all(self, lookback_days: int = 365) -> pd.DataFrame:
        end = datetime.today()
        start = end - timedelta(days=lookback_days)
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")

        # 1) マーケット価格群
        df = self.fetch_multi_assets(start=start_str, end=end_str)

        # 2) FRED（CPI/失業率/FF金利など）
        for sid in FRED_SERIES.values():
            fred_df = self.fetch_fred_data(sid, start_str, end_str)
            if not fred_df.empty and not df.empty:
                df = pd.merge(df, fred_df, on="date", how="left")
                df = df.sort_values("date").ffill()

        # 3) 経済カレンダー
        event_df = self.fetch_event_calendar()
        if not event_df.empty and not df.empty:
            df = pd.merge(df, event_df, on="date", how="left")

        # 4) GNews（日次ニュース件数・ポジネガ件数）
        news_df = self.fetch_gnews_counts(start_str, end_str)
        if not news_df.empty and not df.empty:
            df = pd.merge(df, news_df, on="date", how="left")

        if df is not None:
            df = df.reset_index(drop=True)
            df = align_to_feature_spec(df)

        return df


# --- テスト実行例 ---
if __name__ == "__main__":
    collector = PlanDataCollector()
    df = collector.collect_all(lookback_days=14)
    cols = [c for c in df.columns if "news" in c or c == "date"]
    pd.set_option("display.max_columns", 120)
    print(df[cols].tail())
