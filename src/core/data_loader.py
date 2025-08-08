# core/data_loader.py

import requests
import numpy as np
import logging
import pandas as pd
import json
from src.core.path_config import DATA_DIR   # パス定数をimport
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from typing import Optional, List, Dict, Any
from pathlib import Path  # buffer_pathでstr型が渡される場合に備えて残す（外部指定ありの場合のみ）

DEFAULT_BUFFER_PATH = DATA_DIR / "market_data_buffer.json"  # バッファはdata配下に統一

class MarketDataFetcher:
    """市場データをAPI経由で取得し、トレンドを解析する"""

    def __init__(self, api_key: Optional[str] = None, buffer_path: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        # buffer_pathにstrやPathが来ても絶対パスにする
        self.buffer_path = Path(buffer_path) if buffer_path else DEFAULT_BUFFER_PATH
        self.price_history: List[float] = []
        self.logger = logging.getLogger("MarketDataFetcher")
        self.logger.setLevel(logging.INFO)
        if not self.logger.hasHandlers():
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s'))
            self.logger.addHandler(handler)

        # 起動時にバッファロード
        self.load_price_history()

    # --- バッファのシリアライズ ---
    def save_price_history(self):
        try:
            with open(self.buffer_path, "w", encoding="utf-8") as f:
                json.dump(self.price_history, f)
            self.logger.info(f"価格履歴バッファを保存しました: {self.buffer_path}")
        except Exception as e:
            self.logger.error(f"価格履歴バッファ保存失敗: {e}")

    def load_price_history(self):
        try:
            if self.buffer_path.exists():
                with open(self.buffer_path, "r", encoding="utf-8") as f:
                    self.price_history = json.load(f)
                self.logger.info(f"価格履歴バッファを復元しました: {self.buffer_path}")
            else:
                self.price_history = []
        except Exception as e:
            self.logger.error(f"価格履歴バッファ復元失敗: {e}")
            self.price_history = []

    def fetch_data(self, symbol: str = "USDJPY") -> Optional[Dict[str, Any]]:
        """
        5分足データ1点＋直近10本のvolatility等を取得
        正常時: Dict[str, Any] / エラー時: None
        """
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

            # --- 直近10本クローズ/価格履歴取得 ---
            closes = [float(v["4. close"]) for v in list(time_series.values())[:10]]
            price = closes[0]
            volatility = np.std(closes)

            self.price_history.append(price)
            if len(self.price_history) > 50:
                self.price_history.pop(0)
            self.save_price_history()

            trend_prediction = self.analyze_trend(self.price_history)

            # --- トレンド方向スコア ---
            trend_map = {"bullish": 1.0, "neutral": 0.0, "bearish": -1.0}
            trend_score = trend_map.get(trend_prediction, 0.0)

            # --- 簡易SMAスコア ---
            sma_short = np.mean(closes[:3]) if len(closes) >= 3 else closes[0]
            sma_long = np.mean(closes) if closes else closes[0]
            sma_score = float(np.tanh(sma_short - sma_long))  # -1～+1程度に圧縮

            # --- 合成トレンド強度（volatility+トレンド方向+SMA差分）---
            trend_strength = float(volatility + trend_score + sma_score)

            return {
                "price": price,
                "volatility": float(volatility),
                "trend_strength": trend_strength,
                "trend_direction_score": trend_score,
                "sma_score": sma_score,
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

    def fetch_daily_data(
        self, from_symbol: str = "USD", to_symbol: str = "JPY", max_days: int = 90
    ) -> pd.DataFrame:
        """
        Alpha Vantage から日次為替データ（終値）を取得
        正常時: DataFrame(columns=["date", "close"])
        異常時: columns=["date", "close"]の空DataFrame
        """
        EMPTY_DF = pd.DataFrame(columns=["date", "close"])

        if not self.api_key:
            self.logger.error("APIキーが設定されていません。")
            return EMPTY_DF

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

            if "Note" in data:
                self.logger.warning(f"Alpha Vantage APIリミット制限に到達: {data['Note']}")
                return EMPTY_DF

            if "Time Series FX (Daily)" not in data:
                self.logger.warning("為替日次データが見つかりません")
                return EMPTY_DF

            raw = data["Time Series FX (Daily)"]
            records = [
                {"date": date, "close": float(info["4. close"])}
                for date, info in raw.items()
            ]
            df = pd.DataFrame(records)
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").reset_index(drop=True)
            return df.tail(max_days)[["date", "close"]]

        except Exception as e:
            self.logger.error(f"日次データ取得エラー: {e}")
            return EMPTY_DF
