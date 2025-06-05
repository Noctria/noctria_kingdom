# data/market_data_fetcher.py

import requests
import pandas as pd

class MarketDataFetcher:
    """
    市場データを外部APIから取得し、整形するクラス。
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://example.com/api"  # 実際のAPIエンドポイントに置換
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def get_historical_data(self, symbol="USDJPY", interval="1h", limit=100):
        """
        過去の市場データを取得
        :param symbol: 通貨ペアなど
        :param interval: データ間隔（例: 1h, 1d）
        :param limit: データ数
        :return: np.ndarray (例: (limit, 特徴量数))
        """
        endpoint = f"{self.base_url}/marketdata"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        response = requests.get(endpoint, headers=self.headers, params=params)

        if response.status_code != 200:
            print(f"❌ APIリクエスト失敗: {response.status_code}")
            return None

        data = response.json()
        df = pd.DataFrame(data["prices"])
        print(f"✅ 取得データ: {df.shape}")

        # 例: 不要列の除去や並び替え
        if "timestamp" in df.columns:
            df = df.drop(columns=["timestamp"])

        # 正規化や欠損値補完（例）
        df.fillna(method="ffill", inplace=True)

        return df.values  # NumPy配列に変換して返す
