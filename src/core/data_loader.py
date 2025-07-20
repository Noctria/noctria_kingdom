# core/data_loader.py

import requests
import numpy as np
import logging
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from typing import Optional, List, Dict, Any

class MarketDataFetcher:
    """市場データをAPI経由で取得し、トレンドを解析する"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        self.price_history: List[float] = []

        self.logger = logging.getLogger("MarketDataFetcher")
        self.logger.setLevel(logging.INFO)
        if not self.logger.hasHandlers():
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s'))
            self.logger.addHandler(handler)

    def fetch_data(self, symbol: str = "USDJPY") -> Optional[Dict[str, Any]]:
        if not self.api_key:
            self.logger.error("APIキーが設定されていません。")
            return None

        params = {
            "function": "FX_INTRADAY",
            "from_symbol": symbol[:3],
            "to_symbol": symbol[3:],
            "interval": "5min",
            "apikey": self.api_key
        }
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            if response.status_code != 200:
                self.logger.error(f"データ取得失敗: status={response.status_code}")
                return None

            data = response.json()

            # --- レートリミット（APIリミット）判定 ---
            if "Note" in data:
                self.logger.warning(f"Alpha Vantage APIリミット制限に到達: {data['Note']}")
                return None

            time_series = data.get("Time Series FX (5min)")
            if not time_series:
                self.logger.error("APIレスポンスに 'Time Series FX (5min)' がありません。")
                return None

            latest_key = sorted(time_series.keys())[-1]
            price = float(time_series[latest_key]["4. close"])
            closes = [float(v["4. close"]) for v in list(time_series.values())[:10]]
            volatility = np.std(closes)

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
        except Exception as e:
            self.logger.error(f"データ取得時にエラー発生: {e}")
            return None

    def analyze_trend(self, price_history: List[float]) -> str:
        arr = np.array(price_history)
        if arr.shape[0] < 10:
            return "neutral"

        try:
            model = ExponentialSmoothing(arr, trend="add", seasonal=None)
            fitted_model = model.fit()
            forecast = fitted_model.forecast(1)[0]
            if forecast > arr[-1]:
                return "bullish"
            elif forecast < arr[-1]:
                return "bearish"
            else:
                return "neutral"
        except Exception as e:
            self.logger.warning(f"トレンド解析失敗: {e}")
            return "neutral"

    def fetch_daily_data(self, from_symbol: str = "USD", to_symbol: str = "JPY", max_days: int = 90) -> pd.DataFrame:
        """
        📅 Alpha Vantage から日次為替データ（終値）を取得
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
            response = requests.get(self.base_url, params=params, timeout=10)
            data = response.json()

            # --- レートリミット（APIリミット）判定 ---
            if "Note" in data:
                self.logger.warning(f"Alpha Vantage APIリミット制限に到達: {data['Note']}")
                return pd.DataFrame()

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
