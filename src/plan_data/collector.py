# src/plan_data/collector.py

import os
import time
import random
from datetime import datetime, timedelta, timezone  # [added] timezone
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

# .env の柔軟読み込み（固定パスが無い/他環境でも動作）
_DEFAULT_DOTENV = "/mnt/d/noctria_kingdom/.env"
if os.path.exists(_DEFAULT_DOTENV):
    load_dotenv(dotenv_path=_DEFAULT_DOTENV)
else:
    load_dotenv()

# FEATURE_SPEC はリスト（標準カラム順）。snake_case で運用。
from plan_data.feature_spec import FEATURE_SPEC
from plan_data.observability import log_plan_run
# ---- observability alerts (emit_alert が無い環境でもフォールバック) ---- [added]
try:
    from plan_data.observability import emit_alert, log_alert  # type: ignore
except Exception:
    from plan_data.observability import log_alert  # type: ignore
    emit_alert = None  # type: ignore
# -------------------------------------------------------------------------
from plan_data.trace import new_trace_id


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

# 収集系しきい値（環境変数で上書き可）------------------------------------ [added]
MAX_DATA_LAG_MIN_DEFAULT = 60
def _get_max_data_lag_min() -> int:
    try:
        return int(os.getenv("NOCTRIA_MAX_DATA_LAG_MIN", str(MAX_DATA_LAG_MIN_DEFAULT)))
    except Exception:
        return MAX_DATA_LAG_MIN_DEFAULT

# アラート発火ヘルパ ------------------------------------------------------- [added]
def _emit(kind: str, reason: str, *, severity: str = "MEDIUM", trace_id: Optional[str] = None, details: Optional[dict] = None) -> None:
    try:
        if emit_alert is not None:  # type: ignore
            emit_alert(
                kind=("PLAN."+kind if not kind.startswith(("PLAN.", "DECISION.", "EXEC.", "AI.")) else kind),
                reason=reason, severity=severity, trace_id=trace_id, details=details
            )  # type: ignore
        else:
            log_alert(policy_name="PLAN."+kind, reason=reason, severity=severity, details=details, trace_id=trace_id)  # type: ignore
    except Exception:
        pass


def align_to_feature_spec(df: pd.DataFrame) -> pd.DataFrame:
    """FEATURE_SPEC（リスト）に合わせて不足カラムは追加（NaN）し、その順序で返す。"""
    columns = FEATURE_SPEC
    for col in columns:
        if col not in df.columns:
            df[col] = pd.NA
    # 余分な列は残したい場合は下行をやめるが、既存仕様では並びを固定
    return df[columns]


# =========================
# Collector
# =========================
class PlanDataCollector:
    """
    FRED 依存を廃止し、価格（yfinance）＋イベントCSV（任意）＋ GNews を主軸に収集する実装。
    返り値: (df, trace_id)
    ログ: obs_plan_runs に phase="collector" / "events" / "news" を記録
    """
    def __init__(
        self,
        event_calendar_csv: Optional[str] = None,
        gnews_api_key: Optional[str] = None,
        cache_dir: Optional[Path] = None,
    ):
        # 経済カレンダー
        self.event_calendar_csv = event_calendar_csv or "data/market/event_calendar.csv"
        try:
            Path(self.event_calendar_csv).parent.mkdir(parents=True, exist_ok=True)
            if not os.path.exists(self.event_calendar_csv):
                print(f"[collector] ℹ️ イベントCSVが見つかりません: {self.event_calendar_csv}（スキップ）")
                # フラグ保持（後でLOWアラート）                                   # [added]
                self._missing_event_csv = True                                    # [added]
            else:                                                                  # [added]
                self._missing_event_csv = False                                   # [added]
        except Exception:                                                          # [added]
            self._missing_event_csv = True                                        # [added]

        # GNews
        self.gnews_api_key = gnews_api_key or os.getenv("GNEWS_API_KEY")
        if not self.gnews_api_key:
            print("[collector] ⚠️ GNEWS_API_KEYが未設定です（ニュース特徴は0埋め/欠損になります）")
            # ここでは即アラートせず、collect_all の最後に一度だけ発火           # [added]

        # キャッシュ格納先
        self.cache_dir = Path(cache_dir or "data/cache")
        (self.cache_dir / "gnews").mkdir(parents=True, exist_ok=True)

        # GNews チューニング（.envで上書き可）
        self.gnews_page_size = int(os.getenv("GNEWS_PAGE_SIZE", "50"))          # 10〜100
        self.gnews_max_pages = int(os.getenv("GNEWS_MAX_PAGES", "2"))           # 1日最大ページ数
        self.gnews_retry = int(os.getenv("GNEWS_RETRY", "3"))                   # リトライ回数
        self.gnews_backoff = float(os.getenv("GNEWS_BACKOFF", "1.5"))           # 指数バックオフ係数
        self.gnews_rate_per_min = int(os.getenv("GNEWS_RATE_PER_MIN", "12"))    # 1分あたり上限（無料: 約12程度）
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

    @staticmethod
    def _missing_ratio(df: Optional[pd.DataFrame]) -> float:
        """データ全体の欠損率。'date' 列は除外。空なら 1.0（全欠損扱い）。"""
        if df is None or df.empty:
            return 1.0
        cols = [c for c in df.columns if c != "date"]
        if not cols:
            return 0.0
        total = len(df) * len(cols)
        if total <= 0:
            return 0.0
        return float(df[cols].isna().sum().sum()) / float(total)

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
        errors = 0
        for key, ticker in symbols.items():
            try:
                # 軽いリトライ（最大3回指数バックオフ）
                last_exc = None
                for attempt in range(3):
                    try:
                        df = yf.download(ticker, start=start, end=end, interval=interval, progress=False, auto_adjust=False)
                        break
                    except Exception as e:
                        last_exc = e
                        time.sleep(0.5 * (1.6 ** attempt))
                else:
                    raise last_exc or RuntimeError("yfinance unknown error")

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
                errors += 1

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
        # CSVフォールバックの読み出し
        csv_path = path.with_suffix(".csv")
        if csv_path.exists():
            try:
                return pd.read_csv(csv_path, parse_dates=["date"])
            except Exception:
                csv_path.unlink(missing_ok=True)
        return None

    def _write_day_cache(self, day: datetime, query_key: str, df: pd.DataFrame) -> None:
        path = self._gnews_day_cache_path(day, query_key)
        try:
            df.to_parquet(path, index=False)
        except Exception:
            # Parquet不可ならCSVにフォールバック（環境依存対策）
            try:
                csv_path = path.with_suffix(".csv")
                df.to_csv(csv_path, index=False)
            except Exception:
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

        # ページング（GNews: page/max param）
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

                    # 1ページ未満なら早期終了
                    if len(articles) < self.gnews_page_size:
                        ok = True
                        break

                    ok = True
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
        - 日毎キャッシュ（Parquet/CSV）
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

        return df[["date", "news_count", "news_positive", "news_negative"]].sort_values("date")

    # ---------- 収集一括 ----------
    def collect_all(self, lookback_days: int = 365, trace_id: Optional[str] = None):
        """
        収集一括。各フェーズ末尾で obs_plan_runs に計測を記録（失敗しても本処理は継続）。
        phase: collector / events / news
        戻り値: (df, trace_id)
        """
        end = datetime.today()
        start = end - timedelta(days=lookback_days)
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")

        # trace_id（未指定なら自動生成：P層のバッチ想定で "MULTI","1d" 固定）
        trace_id = trace_id or new_trace_id(symbol="MULTI", timeframe="1d")

        # 1) マーケット価格群
        t0 = time.time()
        df = self.fetch_multi_assets(start=start_str, end=end_str)
        try:
            log_plan_run(
                None,  # DSNは NOCTRIA_OBS_PG_DSN を既定に
                phase="collector",
                rows=len(df) if df is not None else 0,
                dur_sec=int(time.time() - t0),
                missing_ratio=self._missing_ratio(df),
                error_rate=0.0,  # TODO: 取得失敗カウントから算出
                trace_id=trace_id,
            )
        except Exception:
            pass

        # --- 価格データに対する品質アラート（EMPTY/DATA_LAG） ---------------- [added]
        try:
            if df is None or df.empty:
                _emit("COLLECT.EMPTY", "no market price rows fetched", severity="HIGH", trace_id=trace_id,
                      details={"lookback_days": lookback_days})
            else:
                # 最新日付の遅延（分）を計測（UTC基準で頑健に）
                last_ts = pd.to_datetime(df["date"].dropna()).max()
                if pd.isna(last_ts):
                    _emit("COLLECT.EMPTY_DATE", "market df has no valid 'date'", severity="HIGH", trace_id=trace_id)
                else:
                    # 現在UTCと比較
                    now_utc = datetime.now(timezone.utc)
                    last_utc = last_ts.tz_convert("UTC") if getattr(last_ts, "tzinfo", None) else last_ts.tz_localize("UTC")
                    lag_min = int((now_utc - last_utc).total_seconds() // 60)
                    max_lag = _get_max_data_lag_min()
                    if lag_min > max_lag:
                        _emit("COLLECT.DATA_LAG",
                              f"data_lag_min={lag_min} > max={max_lag}",
                              severity=("HIGH" if lag_min > max_lag*2 else "MEDIUM"),
                              trace_id=trace_id,
                              details={"last_date_utc": str(last_utc), "lag_min": lag_min, "max_allowed_min": max_lag})
        except Exception:
            pass
        # ---------------------------------------------------------------------

        # 2) 経済カレンダー（任意）
        t1 = time.time()
        event_df = self.fetch_event_calendar()
        if not event_df.empty and not df.empty:
            df = pd.merge(df, event_df, on="date", how="left")
        try:
            log_plan_run(
                None,
                phase="events",
                rows=len(df) if df is not None else 0,
                dur_sec=int(time.time() - t1),
                missing_ratio=self._missing_ratio(df),
                error_rate=0.0,
                trace_id=trace_id,
            )
        except Exception:
            pass

        # 3) GNews（日次ニュース件数・ポジネガ件数）
        t2 = time.time()
        news_df = self.fetch_gnews_counts(start_str, end_str)
        if not news_df.empty and not df.empty:
            df = pd.merge(df, news_df, on="date", how="left")
        try:
            log_plan_run(
                None,
                phase="news",
                rows=len(df) if df is not None else 0,
                dur_sec=int(time.time() - t2),
                missing_ratio=self._missing_ratio(df),
                error_rate=0.0,
                trace_id=trace_id,
            )
        except Exception:
            pass

        # --- 補助アラート：CSV未配置／GNews無効 -------------------------------- [added]
        try:
            if getattr(self, "_missing_event_csv", False):
                _emit("COLLECT.EVENTS_MISSING_CSV",
                      f"event CSV not found: {self.event_calendar_csv}",
                      severity="LOW", trace_id=trace_id)
            if not self.gnews_api_key:
                _emit("COLLECT.NEWS_DISABLED",
                      "GNEWS_API_KEY not set; news features will be zeros/missing",
                      severity="LOW", trace_id=trace_id)
        except Exception:
            pass
        # ---------------------------------------------------------------------

        if df is not None:
            df = df.reset_index(drop=True)
            df = align_to_feature_spec(df)
            # 下流へtrace_idを明示的に受け渡す
            try:
                df.attrs["trace_id"] = trace_id
            except Exception:
                pass

        # タプル返し（dfのみでも使えるが、trace_idも明示的に返す）
        return df, trace_id


# --- テスト実行例 ---
if __name__ == "__main__":
    collector = PlanDataCollector()
    df, tid = collector.collect_all(lookback_days=14)
    cols = [c for c in df.columns if "news" in c or c == "date"]
    pd.set_option("display.max_columns", 120)
    print("trace_id:", df.attrs.get("trace_id"), tid)
    print(df[cols].tail())
