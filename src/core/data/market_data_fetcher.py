# 変更点: fetch(..., source="yfinance") に "alphavantage" を追加し、既存 data_loader を再利用

from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
import pandas as pd
import yfinance as yf
from src.core.logger import setup_logger

@dataclass
class FetchMeta:
    symbol: str
    interval: str
    period: str
    source: str = "yfinance"
    note: str = ""

class MarketDataFetcher:
    def __init__(self, alphavantage_api_key: Optional[str] = None, retries: int = 3, wait_sec: int = 2, tz: str = "UTC"):
        self.logger = setup_logger("MarketDataFetcher")
        self.alphavantage_api_key = alphavantage_api_key
        self.retries = retries
        self.wait_sec = wait_sec
        self.tz = tz

    def fetch(
        self,
        symbol: str = "USDJPY=X",
        interval: str = "1h",
        period: str = "1mo",
        lower_case: bool = False,
        fillna: bool = True,
        source: str = "yfinance",
    ) -> Tuple[pd.DataFrame, FetchMeta]:
        if source == "alphavantage":
            # 既存の Alpha Vantage 実装をブリッジ（USDJPY固定でもOK / 後で一般化）
            from src.core.data_loader import MarketDataFetcher as _AlphaV  # 互換レイヤ or 既存クラス
            av = _AlphaV(api_key=self.alphavantage_api_key)
            # Alpha Vantage は 5min 固定実装なので近い粒度に合わせる
            rec = av.fetch_data(symbol="USDJPY")  # 既存APIを尊重
            if not rec:
                return pd.DataFrame(), FetchMeta(symbol="USDJPY", interval="5min", period="N/A", source="alphavantage", note="empty")
            # 直近の値・派生指標のみなので、OHLCVに準じたダミーを構成（必要なら data_loader 側で日次OHLC取得を利用）
            df = pd.DataFrame(
                [{"Close": rec["price"], "Open": rec["price"], "High": rec["price"], "Low": rec["price"], "Volume": 0}],
                index=pd.DatetimeIndex([pd.Timestamp.utcnow()], tz="UTC")
            )
            if lower_case:
                df = df.rename(columns={c: c.lower() for c in df.columns})
            return df, FetchMeta(symbol="USDJPY", interval="5min", period="N/A", source="alphavantage")

        # --- 既存のyfinance経路（従来どおり） ---
        self.logger.info(f"📥 fetch: symbol={symbol}, interval={interval}, period={period}")
        df = None; last_err: Optional[Exception] = None
        for attempt in range(1, self.retries + 1):
            try:
                df = yf.download(symbol, interval=interval, period=period, progress=False, threads=False)
                if df is not None and not df.empty:
                    break
            except Exception as e:
                last_err = e
                self.logger.warning(f"⚠️ fetch失敗({attempt}/{self.retries}): {e}")
                time.sleep(self.wait_sec)

        if df is None or df.empty:
            note = f"empty{f' err={last_err}' if last_err else ''}"
            return pd.DataFrame(), FetchMeta(symbol=symbol, interval=interval, period=period, source="yfinance", note=note)

        cols = ["Open","High","Low","Close","Volume"]
        df = df.reindex(columns=[c for c in cols if c in df.columns])
        if fillna: df = df.ffill()
        if lower_case: df = df.rename(columns={c: c.lower() for c in df.columns})
        try:
            if self.tz and getattr(df.index, "tz", None) is not None:
                df = df.tz_convert(self.tz)
        except Exception:
            pass
        return df, FetchMeta(symbol=symbol, interval=interval, period=period, source="yfinance")
