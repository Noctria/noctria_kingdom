# data/market_data_fetcher.py

import yfinance as yf
import pandas as pd

class MarketDataFetcher:
    """
    Yahoo Finance経由で市場データを取得し、整形するクラス。
    通貨ペア・株式・指数の取得に対応（例: USDJPY=X, AAPL, ^GSPC）。
    """

    def __init__(self):
        # 初期化設定（必要に応じて拡張可）
        pass

    def get_historical_data(self, symbol="USDJPY=X", interval="1h", period="1mo"):
        """
        過去の市場データを取得
        :param symbol: 例 "USDJPY=X"（ドル円）、"AAPL"（Apple株式）、"^GSPC"（S&P500指数）
        :param interval: データ間隔（例: "1h", "1d", "1wk"）
        :param period: データ期間（例: "1mo", "3mo", "1y"）
        :return: np.ndarray (例: (行数, 列数)) または None
        """
        print(f"📥 データ取得中: symbol={symbol}, interval={interval}, period={period}")
        
        # データ取得
        df = yf.download(symbol, interval=interval, period=period, progress=False)

        if df.empty:
            print(f"⚠️ データが取得できませんでした: {symbol}")
            return None

        # 欠損値を補完
        df.fillna(method="ffill", inplace=True)

        # "Open", "High", "Low", "Close", "Volume"列のみ使用
        df = df[["Open", "High", "Low", "Close", "Volume"]]
        print(f"✅ 取得データ形状: {df.shape}")

        # NumPy配列に変換して返す
        return df.values

    def get_latest_price(self, symbol="USDJPY=X"):
        """
        現在価格（最新の終値）を取得
        :param symbol: 例 "USDJPY=X"
        :return: float または None
        """
        data = self.get_historical_data(symbol=symbol, interval="1d", period="1d")
        if data is not None and len(data) > 0:
            latest_close = data[-1][3]  # "Close"列を取得
            print(f"💰 最新の終値: {latest_close}")
            return latest_close
        return None

if __name__ == "__main__":
    # 簡易テスト
    fetcher = MarketDataFetcher()
    data = fetcher.get_historical_data(symbol="USDJPY=X", interval="1h", period="1mo")
    if data is not None:
        print("🔎 データの一部を表示:")
        print(data[-5:])  # 直近5行

    latest_price = fetcher.get_latest_price(symbol="AAPL")
    print(f"Apple株式の最新終値: {latest_price}")
