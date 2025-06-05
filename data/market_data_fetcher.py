# data/market_data_fetcher.py

import yfinance as yf
import pandas as pd

class MarketDataFetcher:
    """
    Yahoo Finance経由でドル円（USDJPY）データを取得する専用クラス。
    """

    def __init__(self):
        # 特に初期化パラメータはなし
        pass

    def get_usdjpy_historical_data(self, interval="1h", period="1mo"):
        """
        ドル円のヒストリカルデータを取得
        :param interval: データ間隔（例: "1h", "1d"）
        :param period: 取得期間（例: "1mo", "3mo", "1y"）
        :return: np.ndarray (行数, 列数) または None
        """
        symbol = "USDJPY=X"  # Yahoo Financeシンボル
        print(f"📥 USDJPYデータ取得: interval={interval}, period={period}")

        # データ取得
        df = yf.download(symbol, interval=interval, period=period, progress=False)

        if df.empty:
            print("⚠️ USDJPYデータが取得できませんでした")
            return None

        # 欠損値補完
        df.fillna(method="ffill", inplace=True)

        # "Open", "High", "Low", "Close", "Volume" 列のみ抽出
        df = df[["Open", "High", "Low", "Close", "Volume"]]
        print(f"✅ USDJPYデータ取得完了: {df.shape}")

        # NumPy配列で返す
        return df.values

    def get_usdjpy_latest_price(self):
        """
        ドル円の最新の終値を取得
        :return: float または None
        """
        data = self.get_usdjpy_historical_data(interval="1d", period="1d")
        if data is not None and len(data) > 0:
            latest_close = data[-1][3]  # "Close" 列
            print(f"💰 USDJPYの最新終値: {latest_close}")
            return latest_close
        return None

if __name__ == "__main__":
    # テスト例
    fetcher = MarketDataFetcher()

    # ヒストリカルデータ取得テスト
    data = fetcher.get_usdjpy_historical_data(interval="1h", period="1mo")
    if data is not None:
        print("🔎 USDJPY直近データ（最後の5行）:")
        print(data[-5:])

    # 最新終値取得テスト
    latest_price = fetcher.get_usdjpy_latest_price()
    print(f"USDJPY最新終値: {latest_price}")
