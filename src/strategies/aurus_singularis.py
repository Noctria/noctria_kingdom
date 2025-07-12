import numpy as np
import tensorflow as tf
from core.data.market_data_fetcher import MarketDataFetcher

# GPUメモリの動的確保
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
    except RuntimeError as e:
        print(f"GPU メモリ設定エラー: {e}")

class AurusSingularis:
    """🎯 市場トレンド分析と適応戦略設計を行うAI（臣下A）"""

    def __init__(self):
        self._configure_gpu()
        self.model = self._build_model()
        self.market_fetcher = MarketDataFetcher(api_key="YOUR_API_KEY")

    def _configure_gpu(self):
        gpus = tf.config.list_physical_devices('GPU')
        if gpus:
            try:
                for gpu in gpus:
                    tf.config.experimental.set_memory_growth(gpu, True)
            except RuntimeError as e:
                print(f"GPU メモリ設定エラー: {e}")

    def _build_model(self):
        model = tf.keras.Sequential([
            tf.keras.layers.Input(shape=(12,)),
            tf.keras.layers.Dense(128, activation='relu'),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(1, activation='sigmoid')  # 出力0.0〜1.0
        ])
        model.compile(optimizer='adam', loss='mse')
        return model

    def _preprocess_data(self, market_data):
        trend_map = {"bullish": 0.9, "neutral": 0.5, "bearish": 0.1}
        trend_score = trend_map.get(market_data.get("trend_prediction", "neutral"), 0.5)

        values = [
            market_data.get("price", 0.0),
            market_data.get("volume", 0.0),
            market_data.get("sentiment", 0.0),
            market_data.get("trend_strength", 0.0),
            market_data.get("volatility", 0.0),
            market_data.get("order_block", 0.0),
            market_data.get("institutional_flow", 0.0),
            market_data.get("short_interest", 0.0),
            market_data.get("momentum", 0.0),
            trend_score,
            market_data.get("liquidity_ratio", 0.0),
            1.0
        ]
        return np.array(values).reshape(1, -1)

    def process(self, market_data):
        """従来の判断メソッド（BUY/SELL/HOLD）"""
        processed_data = self._preprocess_data(market_data)
        prediction = float(self.model.predict(processed_data)[0][0])
        if prediction > 0.6:
            return "BUY"
        elif prediction < 0.4:
            return "SELL"
        else:
            return "HOLD"

    def propose(self, market_data: dict) -> dict:
        """
        📩 王Noctriaへの献上：トレンドに基づく戦略提案を返す
        """
        processed_data = self._preprocess_data(market_data)
        prediction = float(self.model.predict(processed_data)[0][0])

        if prediction > 0.6:
            signal = "BUY"
        elif prediction < 0.4:
            signal = "SELL"
        else:
            signal = "HOLD"

        return {
            "name": "Aurus",
            "type": "strategy",
            "signal": signal,
            "score": prediction,
            "symbol": market_data.get("symbol", "USDJPY"),
            "priority": "medium"
        }

# ✅ テスト用スタンドアロン実行
if __name__ == "__main__":
    aurus_ai = AurusSingularis()
    mock_market_data = {
        "price": 1.2345, "volume": 1000, "sentiment": 0.8, "trend_strength": 0.7,
        "volatility": 0.15, "order_block": 0.6, "institutional_flow": 0.8,
        "short_interest": 0.5, "momentum": 0.9, "trend_prediction": "bullish",
        "liquidity_ratio": 1.2, "symbol": "USDJPY"
    }
    decision = aurus_ai.propose(mock_market_data)
    print("👑 王への提案:", decision)
