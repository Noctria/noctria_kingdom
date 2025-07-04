import numpy as np
import tensorflow as tf
from core.data_loader import MarketDataFetcher
from core.risk_management import RiskManager

class PrometheusOracle:
    """市場予測を行うAI（改修版）"""
    
    def __init__(self):
        self.model = self._build_model()
        self.market_fetcher = MarketDataFetcher(api_key="YOUR_API_KEY")
        self.risk_manager = RiskManager()

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
        prediction = self.model.predict(processed_data)
        return float(prediction)

    def _preprocess_data(self, market_data):
        """市場データの前処理"""
        trend_map = {"bullish": 0.9, "neutral": 0.5, "bearish": 0.1}
        trend_score = trend_map.get(market_data.get("trend_prediction", "neutral"), 0.5)

        return np.array([
            market_data["price"], market_data["volume"], market_data["sentiment"],
            market_data["trend_strength"], market_data["volatility"], market_data["order_block"],
            market_data["institutional_flow"], market_data["short_interest"], market_data["momentum"],
            trend_score, market_data["liquidity_ratio"], 1
        ]).reshape(1, -1)

# ✅ 改修後の市場予測テスト
if __name__ == "__main__":
    oracle = PrometheusOracle()
    mock_market_data = {
        "price": 1.2345, "volume": 1000, "sentiment": 0.8, "trend_strength": 0.7,
        "volatility": 0.15, "order_block": 0.6, "institutional_flow": 0.8,
        "short_interest": 0.5, "momentum": 0.9, "trend_prediction": "bullish",
        "liquidity_ratio": 1.2
    }
    forecast = oracle.predict_market(mock_market_data)
    print("Market Forecast:", forecast)
