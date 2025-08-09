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

# .env 読み込み（パスは環境に合わせて）
load_dotenv(dotenv_path="/mnt/d/noctria_kingdom/.env")

# FEATURE_SPEC はリスト（標準カラム順）。snake_case で運用想定。
from plan_data.feature_spec import FEATURE_SPEC  # noqa: E402


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

FRED_SERIES: Dict[str, str] = {
    "UNRATE": "UNRATE",
    "FEDFUNDS": "FEDFUNDS",
    "CPI": "CPIAUCSL",
}


def align_to_feature_spec(df: pd.DataFrame) -> pd.DataFrame:
    """
    FEATURE_SPEC（リスト）に合わせて不足カラムは追加（NaN）し、
    最終的にその順序で返す。
    """
    columns = FEATURE_SPEC

    for col in columns:
        if col not in df.columns:
            df[col] = pd.NA

    # 必要であれば型変換は個別に（ここでは行わない）
    return df[columns]


class PlanDataCollector:
    def __init__(self, fred_api_key: Optional[str] = None, event_calendar_csv: Optional[str] = None):
        self.fred_api_key = fred_api_key or os.getenv("FRED_API_KEY")
        if not self.fred_api_key:
            print("[collector] ⚠️ FRED_API_KEYが未設定です")
        self.event_calendar_csv = event_calendar_csv or "data/market/event_calendar.csv"
        self.newsapi_key = os.getenv("NEWSAPI_KEY")
        if not self.newsapi_key:
            print("[collector] ⚠️ NEWSAPI_KEYが未設定です")

    # --------- ヘルパ群 ---------

    @staticmethod
    def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
        """
        yfinance の MultiIndex 列などをフラット化。
        例: ('Close', 'JPY=X') -> 'Close_JPY=X'
        また、非文字列列名は文字列化。
        """
        cols = df.columns
        if isinstance(cols, pd.MultiIndex):
            df = df.copy()
            df.columns = ["_".join([str(c) for c in tup if c is not None and c != ""])
                          for tup in cols]
            return df
        # 単純な列でも、念のため非文字列を文字列化
        if any(not isinstance(c, str) for c in cols):
            df = df.copy()
            df.columns = [str(c) for c in cols]
        return df

    @staticmethod
    def _ensure_date_column(df: pd.DataFrame) -> pd.DataFrame:
        """
        'date' 列を保証。存在しなければ 'Date' / 'Datetime' 等を探して変換。
        既に 'date' があれば to_datetime だけ実施。
        """
        df = df.copy()
        candidates = ["date", "Date", "Datetime", "datetime"]
        found = None
        for c in candidates:
            if c in df.columns:
                found = c
                break
        if found is None:
            # yfinance reset_index 後は 'Date' が基本だが、万一無ければそのまま
            return df
        if found != "date":
            df = df.rename(columns={found: "date"})
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df

    @staticmethod
    def _pick_first_matching(df: pd.DataFrame, starts_with: str) -> Optional[str]:
        """
        'Close', 'Close_^GSPC', 'Close_JPY=X' のような列から
        starts_with（lower比較）で最初に一致するものを返す。
        """
        # 完全一致優先（例: 'Close' / 'Volume'）
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
        """
        yfinance で複数アセットの Close/Volume を取得し、date で外部結合。
        Close/Volume が MultiIndex フォーマットでも柔軟に検出する。
        """
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

                # index -> 列へ
                df = df.reset_index()
                # 安全のためフラット化 & date 保証
                df = self._flatten_columns(df)
                df = self._ensure_date_column(df)

                # Close / Volume の柔軟検出
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

                # 数値化
                for c in out.columns:
                    if c != "date":
                        out[c] = pd.to_numeric(out[c], errors="coerce")

                dfs.append(out)

            except Exception as e:
                print(f"[collector] {ticker} の取得中エラー: {e}")

        if not dfs:
            # 空の DataFrame を返す（後続で安全に扱えるよう 'date' 列だけ持たせてもOK）
            return pd.DataFrame(columns=["date"])

        # date で順次外部結合
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

        # 前方補完（経済指標など週次・月次と価格の粒度差をならすため）
        merged = merged.fillna(method="ffill")

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
        """経済カレンダーCSV（カラム例: date, fomc, cpi, nfp, ...）"""
        try:
            df = pd.read_csv(self.event_calendar_csv)
            df.columns = [col.lower() for col in df.columns]
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
            return df
        except Exception as e:
            print(f"[collector] イベントカレンダー取得失敗: {e}")
            return pd.DataFrame()

    def fetch_newsapi_counts(self, start_date: str, end_date: str, query="usd jpy") -> pd.DataFrame:
        """NewsAPIで日次ニュース件数＋ポジ/ネガワード件数を返す"""
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
            return pd.DataFrame(dfs)
        return pd.DataFrame()

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
                df = df.sort_values("date").fillna(method="ffill")

        # 経済カレンダー
        event_df = self.fetch_event_calendar()
        if not event_df.empty and df is not None and not df.empty:
            df = pd.merge(df, event_df, on="date", how="left")

        # NewsAPI（日次ニュース件数・ポジ/ネガ件数）
        news_df = self.fetch_newsapi_counts(start_str, end_str)
        if not news_df.empty and df is not None and not df.empty:
            df = pd.merge(df, news_df, on="date", how="left")

        if df is not None:
            df = df.reset_index(drop=True)
            # collector 側では最終的に標準仕様へ合わせない場合は以下をコメントアウト
            # ただし pipeline 的にここで揃えておくのが安全
            df = align_to_feature_spec(df)

        return df


# --- テスト実行例 ---
if __name__ == "__main__":
    collector = PlanDataCollector()
    df = collector.collect_all(lookback_days=7)
    # テスト: date/news系の末尾確認
    cols = [c for c in df.columns if "news" in c or c == "date"]
    print(df[cols].tail())
