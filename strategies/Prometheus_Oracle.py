import numpy as np
import tensorflow as tf
from data_loader import MarketDataFetcher
from risk_management import RiskManager

class PrometheusOracle:
    """市場予測を行うAI（改修版）"""
    
    def __init__(self):
        self.model = self._build_model()
        self.market_fetcher = MarketDataFetcher(api_key="YOUR_API_KEY")
        self.risk_manager = RiskManager()

    def _build_model(self):
        """強化学習と市場予測を統合したモデル"""
        model = tf.keras.Sequential([
            tf.keras.layers.Dense(128, activation='relu', input_shape=(12,)),  # 特徴量拡張
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
        """市場データの前処理（拡張版: 機関投資家・センチメント・トレンド強度を考慮）"""
        return np.array([
            market_data["price"], market_data["volume"], market_data["sentiment"],
            market_data["trend_strength"], market_data["volatility"], market_data["order_block"],
            market_data["institutional_flow"], market_data["short_interest"], market_data["momentum"],
            market_data["trend_prediction"], market_data["liquidity_ratio"], 1  # 追加特徴量
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
