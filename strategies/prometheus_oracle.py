import numpy as np
import tensorflow as tf
from core.data_loader import MarketDataFetcher
from core.risk_manager import RiskManager
from datetime import datetime, timedelta
import pandas as pd


class PrometheusOracle:
    """
    📈 市場予測を行うAIモデル
    - 強化学習・予測統合モデル（簡易構成）
    - 信頼区間付き日次予測に対応
    """

    def __init__(self):
        self.model = self._build_model()
        self.market_fetcher = MarketDataFetcher(api_key="YOUR_API_KEY")
        self.risk_manager = RiskManager()

    def _build_model(self):
        """📐 予測モデル（ダミー構成、将来は学習済み重みをロード）"""
        model = tf.keras.Sequential([
            tf.keras.layers.Dense(128, activation='relu', input_shape=(12,)),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(1, activation='linear')
        ])
        model.compile(optimizer='adam', loss='mse')
        return model

    def _preprocess_data(self, market_data: dict) -> np.ndarray:
        """🔧 市場データの前処理"""
        trend_map = {"bullish": 0.9, "neutral": 0.5, "bearish": 0.1}
        trend_score = trend_map.get(market_data.get("trend_prediction", "neutral"), 0.5)

        vector = np.array([
            market_data.get("price", 1.0),
            market_data.get("volume", 1000),
            market_data.get("sentiment", 0.5),
            market_data.get("trend_strength", 0.5),
            market_data.get("volatility", 0.2),
            market_data.get("order_block", 0.5),
            market_data.get("institutional_flow", 0.5),
            market_data.get("short_interest", 0.5),
            market_data.get("momentum", 0.5),
            trend_score,
            market_data.get("liquidity_ratio", 1.0),
            1.0  # bias
        ]).reshape(1, -1)

        return vector

    def predict_market(self, market_data: dict) -> float:
        """📊 単一時点の市場予測"""
        processed = self._preprocess_data(market_data)
        prediction = self.model.predict(processed, verbose=0)
        return float(prediction[0][0])

    def predict_with_confidence(self, n_days: int = 14) -> pd.DataFrame:
        """
        📈 日次予測と信頼区間（±標準偏差）付き出力
        - 実データ未使用。ランダム入力によるシミュレーション。
        """
        today = datetime.today()
        records = []

        for i in range(n_days):
            date = today + timedelta(days=i)
            mock_data = self._generate_mock_data(seed=i)
            pred = self.predict_market(mock_data)

            std_dev = 0.8  # 仮の信頼幅
            records.append({
                "date": date.strftime("%Y-%m-%d"),
                "y_pred": round(pred, 4),
                "y_lower": round(pred - std_dev, 4),
                "y_upper": round(pred + std_dev, 4)
            })

        return pd.DataFrame(records)

    def _generate_mock_data(self, seed: int = 0) -> dict:
        """🧪 シミュレーション用ランダム市場データ生成"""
        np.random.seed(seed)
        return {
            "price": np.random.uniform(1.1, 1.3),
            "volume": np.random.uniform(800, 1200),
            "sentiment": np.random.uniform(0, 1),
            "trend_strength": np.random.uniform(0, 1),
            "volatility": np.random.uniform(0.1, 0.3),
            "order_block": np.random.uniform(0, 1),
            "institutional_flow": np.random.uniform(0, 1),
            "short_interest": np.random.uniform(0, 1),
            "momentum": np.random.uniform(0, 1),
            "trend_prediction": np.random.choice(["bullish", "neutral", "bearish"]),
            "liquidity_ratio": np.random.uniform(0.8, 1.5)
        }


# ✅ スクリプトテスト用
if __name__ == "__main__":
    oracle = PrometheusOracle()
    forecast_df = oracle.predict_with_confidence(n_days=5)
    print(forecast_df)
