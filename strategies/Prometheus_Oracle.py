import numpy as np
import pandas as pd
import tensorflow as tf
from data.market_data_fetcher import MarketDataFetcher
from core.risk_management import RiskManagement

class PrometheusOracle:
    """
    MetaAI対応版:
    未来市場予測を担うAIモジュール（ヒストリカルデータ利用）
    """

    def __init__(self):
        self.model = self._build_model()
        self.market_fetcher = MarketDataFetcher()

        # ✅ ヒストリカルデータ取得
        data_array = self.market_fetcher.get_usdjpy_historical_data(interval="1h", period="1mo")
        if data_array is None:
            print("⚠️ データ取得失敗。ダミーデータで初期化します")
            data_array = np.random.normal(loc=100, scale=5, size=(100, 5))

        columns = ["Open", "High", "Low", "Close", "Volume"]
        historical_data = pd.DataFrame(data_array, columns=columns)

        # ✅ リスク管理インスタンス
        self.risk_manager = RiskManagement(historical_data=historical_data)

    def _build_model(self):
        model = tf.keras.Sequential([
            tf.keras.layers.Dense(128, activation='relu', input_shape=(12,)),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(1, activation='linear')
        ])
        model.compile(optimizer='adam', loss='mse')
        return model

    def _preprocess_data(self, market_data):
        """
        市場データの前処理（例: 12次元ベクトル化）
        """
        return np.array([
            market_data.get("price", 0.0),
            market_data.get("volume", 0.0),
            market_data.get("sentiment", 0.0),
            market_data.get("trend_strength", 0.0),
            market_data.get("volatility", 0.0),
            market_data.get("order_block", 0.0),
            market_data.get("institutional_flow", 0.0),
            market_data.get("short_interest", 0.0),
            market_data.get("momentum", 0.0),
            market_data.get("trend_prediction", 0.0),
            market_data.get("liquidity_ratio", 0.0),
            1.0
        ]).reshape(1, -1)

    def decide_action(self, market_data):
        """
        ✅ MetaAI統合用インターフェース:
        市場データを受け取り、未来スコアから最適戦略を返す
        """
        processed_data = self._preprocess_data(market_data)
        prediction = self.model.predict(processed_data, verbose=0)
        score = float(prediction)

        # 簡易ロジック例
        if score > 0.6:
            return "BUY"
        elif score < 0.4:
            return "SELL"
        else:
            return "HOLD"

# ✅ 改修後のテスト実行
if __name__ == "__main__":
    oracle = PrometheusOracle()
    mock_market_data = {
        "price": 1.2345, "volume": 1000, "sentiment": 0.8, "trend_strength": 0.7,
        "volatility": 0.15, "order_block": 0.6, "institutional_flow": 0.8,
        "short_interest": 0.5, "momentum": 0.9, "trend_prediction": 0.6,
        "liquidity_ratio": 1.2
    }
    decision = oracle.decide_action(mock_market_data)
    print("Market Decision:", decision)
