import numpy as np
import pandas as pd
import tensorflow as tf
from data.market_data_fetcher import MarketDataFetcher
from core.risk_management import RiskManagement

class PrometheusOracle:
    """市場予測を行うAI（ヒストリカルデータ利用版）"""

    def __init__(self):
        self.model = self._build_model()

        # ✅ MarketDataFetcherにAPIキーは不要
        self.market_fetcher = MarketDataFetcher()

        # ✅ ヒストリカルデータ取得（1時間足・1ヶ月分）
        data_array = self.market_fetcher.get_usdjpy_historical_data(interval="1h", period="1mo")
        if data_array is None:
            print("⚠️ データ取得失敗。ダミーデータで初期化します")
            data_array = np.random.normal(loc=100, scale=5, size=(100, 5))

        columns = ["Open", "High", "Low", "Close", "Volume"]
        historical_data = pd.DataFrame(data_array, columns=columns)

        # ✅ RiskManagementに渡す
        self.risk_manager = RiskManagement(historical_data=historical_data)

    def _build_model(self):
        """強化学習と市場予測を統合したモデル"""
        model = tf.keras.Sequential([
            tf.keras.layers.Dense(128, activation='relu', input_shape=(12,)),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(1, activation='linear')
        ])
        model.compile(optimizer='adam', loss='mse')
        return model

    def predict_market(self, market_data):
        """市場データを解析し、未来の価格を予測"""
        processed_data = self._preprocess_data(market_data)
        prediction = self.model.predict(processed_data, verbose=0)
        return float(prediction)

    def _preprocess_data(self, market_data):
        """市場データの前処理"""
        return np.array([
            market_data["price"], market_data["volume"], market_data["sentiment"],
            market_data["trend_strength"], market_data["volatility"], market_data["order_block"],
            market_data["institutional_flow"], market_data["short_interest"], market_data["momentum"],
            market_data["trend_prediction"], market_data["liquidity_ratio"], 1
        ]).reshape(1, -1)

# ✅ 改修後の市場予測テスト
if __name__ == "__main__":
    oracle = PrometheusOracle()
    mock_market_data = {
        "price": 1.2345, "volume": 1000, "sentiment": 0.8, "trend_strength": 0.7,
        "volatility": 0.15, "order_block": 0.6, "institutional_flow": 0.8,
        "short_interest": 0.5, "momentum": 0.9, "trend_prediction": 0.6,  # 文字列ではなく数値に変換
        "liquidity_ratio": 1.2
    }
    forecast = oracle.predict_market(mock_market_data)
    print("Market Forecast:", forecast)
