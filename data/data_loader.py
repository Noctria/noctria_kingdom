import requests
import numpy as np
import logging
from statsmodels.tsa.holtwinters import ExponentialSmoothing

class MarketDataFetcher:
    """市場変動パターンを分析し、データ取得精度を向上"""

    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.financialdata.com/market"
        self.logger = logging.getLogger("MarketDataFetcher")
        self.logger.setLevel(logging.DEBUG)
        self.price_history = []  # 過去価格データを保存

    def fetch_data(self, symbol="USDJPY"):
        """市場データを取得し、変動パターンに基づいて最適化"""
        url = f"{self.base_url}?symbol={symbol}&apikey={self.api_key}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            processed_data = self.process_data(data)

            update_interval = self.dynamic_update_frequency(processed_data["price"])
            self.logger.info(f"Next data fetch in {update_interval} seconds")

            return processed_data
        else:
            self.logger.error("Failed to fetch market data")
            return None

    def process_data(self, data):
        """市場データを整形し、ノイズをフィルタリング"""
        price = data["latest_price"]
        self.price_history.append(price)
        if len(self.price_history) > 50:
            self.price_history.pop(0)  # 最新50データのみ保存

        trend_prediction = self.analyze_trend(self.price_history)

        return {
            "price": price,
            "volatility": data["volatility"],
            "trend_strength": data["trend_score"],
            "news_sentiment": data["sentiment_score"],
            "trend_prediction": trend_prediction
        }

    def analyze_trend(self, price_history):
        """時系列解析を使い、市場のトレンドを予測"""
        if len(price_history) < 10:
            return "neutral"

        model = ExponentialSmoothing(price_history, trend="add")
        fitted_model = model.fit()
        trend_forecast = fitted_model.forecast(1)[0]

        if trend_forecast > price_history[-1]:
            return "bullish"
        elif trend_forecast < price_history[-1]:
            return "bearish"
        else:
            return "neutral"

# ✅ `data_loader.py` の市場変動分析テスト
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    api_key = "YOUR_API_KEY"
    fetcher = MarketDataFetcher(api_key)

    while True:
        market_data = fetcher.fetch_data()
        if market_data:
            print(f"Fetched Market Data: {market_data}")
