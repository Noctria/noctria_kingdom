# src/core/data/market_data_fetcher.py
# 変更点:
# - Alpha Vantage ブリッジでシンボル正規化を追加（"USDJPY" / "USDJPY=X" / "USD/JPY" など）
# - 既存 data_loader の実装を再利用しつつ、返却は (df, FetchMeta)

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
    def __init__(
        self,
        alphavantage_api_key: Optional[str] = None,
        retries: int = 3,
        wait_sec: int = 2,
        tz: str = "UTC",
    ):
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
        """
        汎用フェッチャ（現状は yfinance / Alpha Vantage ブリッジ）
        Returns: (df, meta)
          df columns: ["Open","High","Low","Close","Volume"] もしくは lower_case=True で小文字化
          df index  : tz-aware（yfinanceは元TZ、必要に応じて tz_convert）
        """

        # ---------- Alpha Vantage ブリッジ ----------
        if source == "alphavantage":
            # 既存の Alpha Vantage 実装をブリッジ（src.core.data_loader.MarketDataFetcher）
            from src.core.data_loader import MarketDataFetcher as _AlphaV  # 互換レイヤ or 既存クラス
            av = _AlphaV(api_key=self.alphavantage_api_key)

            # symbol 正規化： "USDJPY" / "USDJPY=X" / "USD/JPY" などから from/to を抽出
            raw = symbol.upper().replace("=X", "").replace("/", "")
            if len(raw) >= 6:
                from_sym, to_sym = raw[:3], raw[3:6]
            else:
                from_sym, to_sym = "USD", "JPY"  # フォールバック
            av_symbol = f"{from_sym}{to_sym}"

            # Alpha Vantage 側は 5min の1点＋派生指標のみ（既存実装の fetch_data を尊重）
            rec = av.fetch_data(symbol=av_symbol)
            if not rec:
                return (
                    pd.DataFrame(),
                    FetchMeta(
                        symbol=av_symbol,
                        interval="5min",
                        period="N/A",
                        source="alphavantage",
                        note="empty",
                    ),
                )

            # 直近1点のクローズしかないため、OHLCV準拠の最小構成を返す
            df = pd.DataFrame(
                [
                    {
                        "Close": rec["price"],
                        "Open": rec["price"],
                        "High": rec["price"],
                        "Low": rec["price"],
                        "Volume": 0,
                    }
                ],
                index=pd.DatetimeIndex([pd.Timestamp.utcnow()], tz="UTC"),
            )
            if lower_case:
                df = df.rename(columns={c: c.lower() for c in df.columns})
            return df, FetchMeta(
                symbol=av_symbol, interval="5min", period="N/A", source="alphavantage"
            )

        # ---------- yfinance 経路（標準） ----------
        self.logger.info(f"📥 fetch: symbol={symbol}, interval={interval}, period={period}")
        df = None
        last_err: Optional[Exception] = None

        for attempt in range(1, self.retries + 1):
            try:
                df = yf.download(
                    symbol, interval=interval, period=period, progress=False, threads=False
                )
                if df is not None and not df.empty:
                    break
            except Exception as e:
                last_err = e
                self.logger.warning(f"⚠️ fetch失敗({attempt}/{self.retries}): {e}")
                time.sleep(self.wait_sec)

        if df is None or df.empty:
            note = f"empty{f' err={last_err}' if last_err else ''}"
            return (
                pd.DataFrame(),
                FetchMeta(
                    symbol=symbol, interval=interval, period=period, source="yfinance", note=note
                ),
            )

        cols = ["Open", "High", "Low", "Close", "Volume"]
        df = df.reindex(columns=[c for c in cols if c in df.columns])

        if fillna:
            df = df.ffill()

        if lower_case:
            df = df.rename(columns={c: c.lower() for c in df.columns})

        # yfinanceはTZ付きIndexの場合が多い。必要なら指定TZへ変換。
        try:
            if self.tz and getattr(df.index, "tz", None) is not None:
                df = df.tz_convert(self.tz)
        except Exception:
            # 既に同一TZ or naive index の場合は無視
            pass

        return df, FetchMeta(symbol=symbol, interval=interval, period=period, source="yfinance")
