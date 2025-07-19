# core/data_loader.py

import requests
import numpy as np
import logging
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

class MarketDataFetcher:
    """市場データをAPI経由で取得し、トレンドを解析する"""

    # ❗️【修正点】api_keyを必須引数からオプション引数に変更 (api_key=None を追加)
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        self.logger = logging.getLogger("MarketDataFetcher")
        self.logger.setLevel(logging.DEBUG)
        self.price_history = []

    def fetch_data(self, symbol="USDJPY"):
        if not self.api_key:
            self.logger.error("APIキーが設定されていません。")
            return None

        params = {
            "function": "FX_INTRADAY",
            "from_symbol": "USD",
            "to_symbol": "JPY",
            "interval": "5min",
            "apikey": self.api_key
        }
        response = requests.get(self.base_url, params=params)

        if response.status_code == 200:
            try:
                data = response.json()
                price = float(list(data["Time Series FX (5min)"].values())[0]["4. close"])
            except Exception as e:
                self.logger.error(f"データ解析エラー: {e}")
                return None

            volatility = np.std([float(v["4. close"]) for v in list(data["Time Series FX (5min)"].values())[:10]])
            self.price_history.append(price)
            if len(self.price_history) > 50:
                self.price_history.pop(0)

            trend_prediction = self.analyze_trend(self.price_history)

            return {
                "price": price,
                "volatility": volatility,
                "trend_strength": volatility,
                "news_sentiment": 0.5,
                "trend_prediction": trend_prediction
            }
        else:
            self.logger.error("データ取得失敗")
            return None

    def analyze_trend(self, price_history):
        if len(price_history) < 10:
            return "neutral"

        model = ExponentialSmoothing(price_history, trend="add")
        fitted_model = model.fit()
        forecast = fitted_model.forecast(1)[0]

        if forecast > price_history[-1]:
            return "bullish"
        elif forecast < price_history[-1]:
            return "bearish"
        else:
            return "neutral"

    def fetch_daily_data(self, from_symbol="USD", to_symbol="JPY", max_days=90) -> pd.DataFrame:
        """
        📅 Alpha Vantage から日次為替データ（終値）を取得
        :param from_symbol: 通貨（例: USD）
        :param to_symbol: 通貨（例: JPY）
        :param max_days: 取得する最大日数（新しい順）
        :return: DataFrame（date, close）
        """
        if not self.api_key:
            self.logger.error("APIキーが設定されていません。")
            return pd.DataFrame()

        params = {
            "function": "FX_DAILY",
            "from_symbol": from_symbol,
            "to_symbol": to_symbol,
            "apikey": self.api_key,
            "outputsize": "compact"
        }

        try:
            response = requests.get(self.base_url, params=params)
            data = response.json()

            if "Time Series FX (Daily)" not in data:
                self.logger.warning("為替日次データが見つかりません")
                return pd.DataFrame()

            raw = data["Time Series FX (Daily)"]
            records = [
                {"date": date, "close": float(info["4. close"])}
                for date, info in raw.items()
            ]
            df = pd.DataFrame(records)
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").reset_index(drop=True)

            return df.tail(max_days)

        except Exception as e:
            self.logger.error(f"日次データ取得エラー: {e}")
            return pd.DataFrame()
