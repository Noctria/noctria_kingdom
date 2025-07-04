# core/data_loader.py

import requests
import numpy as np
import logging
from statsmodels.tsa.holtwinters import ExponentialSmoothing

class MarketDataFetcher:
    """市場データをAPI経由で取得し、トレンドを解析する"""

    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        self.logger = logging.getLogger("MarketDataFetcher")
        self.logger.setLevel(logging.DEBUG)
        self.price_history = []

    def fetch_data(self, symbol="USDJPY"):
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
