# src/core/data/market_data_fetcher.py
import time
from datetime import timezone
from typing import Optional, Dict, Any

import pandas as pd
import yfinance as yf

from src.core.logger import setup_logger  # ← src. に統一


class MarketDataFetcher:
    """
    📡 Noctria Kingdom 市場データ取得（Yahoo Finance）
    - 正規API: fetch(symbol, interval, period)
    - 互換API: get_usdjpy_historical_data / get_usdjpy_latest_price
    """
    def __init__(self, alphavantage_api_key: Optional[str] = None, retries: int = 3, wait_sec: float = 2.0):
        self.logger = setup_logger("MarketDataFetcher")
        self.alphavantage_api_key = alphavantage_api_key  # いまは未使用（将来拡張用）
        self.retries = max(1, retries)
        self.wait_sec = max(0.5, float(wait_sec))

    def fetch(self, symbol: str, interval: str = "1h", period: str = "1mo") -> Optional[pd.DataFrame]:
        """
        汎用取得API（推奨）
        Returns:
            tz-aware(UTC) index の DataFrame(columns=["open","high","low","close","volume"])
            取得失敗時は None
        """
        self.logger.info(f"📥 fetch: symbol={symbol}, interval={interval}, period={period}")
        df = None
        backoff = self.wait_sec

        for attempt in range(1, self.retries + 1):
            try:
                tmp = yf.download(symbol, interval=interval, period=period, progress=False, threads=False)
                if tmp is not None and not tmp.empty:
                    df = tmp.copy()
                    break
                self.logger.warning(f"空データ受信（{attempt}/{self.retries}）")
            except Exception as e:
                self.logger.warning(f"⚠️ 通信失敗（{attempt}/{self.retries}）: {e}")
            time.sleep(backoff)
            backoff *= 1.6  # 簡易指数バックオフ

        if df is None or df.empty:
            self.logger.error("🚫 データ取得に失敗しました")
            return None

        # 正規化：欠損前埋め＋列名＋TZ
        df = df.fillna(method="ffill")
        cols_map = {"Open": "open", "High": "high", "Low": "low", "Close": "close", "Adj Close": "close", "Volume": "volume"}
        df = df.rename(columns=cols_map)
        # 必要列だけに絞る（不足があれば raise せずスキップ）
        keep = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
        df = df[keep]

        # tz-aware (UTC)
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        else:
            df.index = df.index.tz_convert("UTC")

        self.logger.info(f"✅ 取得成功: shape={df.shape}, from={df.index.min()} to={df.index.max()}")
        return df

    # ---- 互換API（既存呼び出しの維持） ----
    def get_usdjpy_historical_data(self, interval: str = "1h", period: str = "1mo") -> Optional[pd.DataFrame]:
        """互換：USDJPYヒストリカル"""
        return self.fetch(symbol="USDJPY=X", interval=interval, period=period)

    def get_usdjpy_latest_price(self) -> Optional[float]:
        """互換：USDJPYの直近終値"""
        df = self.fetch(symbol="USDJPY=X", interval="1d", period="5d")
        if df is not None and not df.empty and "close" in df.columns:
            latest = float(df["close"].iloc[-1])
            self.logger.info(f"💰 直近終値: {latest}")
            return latest
        return None


if __name__ == "__main__":
    f = MarketDataFetcher()
    d = f.get_usdjpy_historical_data()
    if d is not None:
        d.tail().to_csv("USDJPY_recent.csv")
        print("✅ saved: USDJPY_recent.csv")
        print(d.tail())
    print("latest:", f.get_usdjpy_latest_price())
