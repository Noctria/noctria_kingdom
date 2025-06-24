import yfinance as yf
import pandas as pd
import time
from core.logger import setup_logger

class MarketDataFetcher:
    """
    📡 Noctria Kingdomの市場情報通信塔：Yahoo Finance経由でUSDJPYの市場情報を取得。
    """
    def __init__(self, retries=3, wait_sec=2):
        self.logger = setup_logger("MarketDataFetcher", "/opt/airflow/logs/market_data_fetcher.log")
        self.retries = retries
        self.wait_sec = wait_sec

    def get_usdjpy_historical_data(self, interval="1h", period="1mo"):
        """
        ドル円のヒストリカルデータを取得
        """
        symbol = "USDJPY=X"
        self.logger.info(f"📥 市場通信開始: {symbol}, interval={interval}, period={period}")

        df = None
        for attempt in range(1, self.retries + 1):
            try:
                df = yf.download(symbol, interval=interval, period=period, progress=False)
                if not df.empty:
                    break
            except Exception as e:
                self.logger.warning(f"⚠️ 通信失敗（{attempt}/{self.retries}）: {e}")
                time.sleep(self.wait_sec)

        if df is None or df.empty:
            self.logger.error("🚫 USDJPYの市場情報取得に失敗しました")
            return None

        df.fillna(method="ffill", inplace=True)
        df = df[["Open", "High", "Low", "Close", "Volume"]]
        self.logger.info(f"✅ データ取得成功: {df.shape}")
        return df.values

    def get_usdjpy_latest_price(self):
        """
        USDJPYの直近の終値を取得
        """
        data = self.get_usdjpy_historical_data(interval="1d", period="1d")
        if data is not None and len(data) > 0:
            latest_close = data[-1][3]
            self.logger.info(f"💰 直近終値（Close）: {latest_close}")
            return latest_close
        return None

if __name__ == "__main__":
    fetcher = MarketDataFetcher()
    data = fetcher.get_usdjpy_historical_data()
    if data is not None:
        print("🔎 USDJPY直近データ:")
        print(data[-5:])
    print("USDJPY 最新終値:", fetcher.get_usdjpy_latest_price())
