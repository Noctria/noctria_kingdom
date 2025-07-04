import numpy as np
import pandas as pd
import tensorflow as tf
from data.market_data_fetcher import MarketDataFetcher
from core.risk_managemer import RiskManager
from core.logger import setup_logger  # 👑 ロガーを導入

class PrometheusOracle:
    """🔮 市場予測を行うAI（ヒストリカルデータ利用版・MetaAI改修版）"""

    def __init__(self):
        self.logger = setup_logger("PrometheusLogger", "/opt/airflow/logs/PrometheusLogger.log")
        self.model = self._build_model()
        self.market_fetcher = MarketDataFetcher()

        data_array = self.market_fetcher.get_usdjpy_historical_data(interval="1h", period="1mo")
        if data_array is None:
            self.logger.warning("⚠️ データ取得失敗。ダミーデータで初期化します")
            data_array = np.random.normal(loc=100, scale=5, size=(100, 5))

        columns = ["Open", "High", "Low", "Close", "Volume"]
        historical_data = pd.DataFrame(data_array, columns=columns)

        self.risk_manager = RiskManagement(historical_data=historical_data)

    def _build_model(self):
        """未来予測用のシンプルなMLPモデル"""
        model = tf.keras.Sequential([
            tf.keras.layers.Dense(128, activation='relu', input_shape=(12,)),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(1, activation='linear')
        ])
        model.compile(optimizer='adam', loss='mse')
        return model

    def process(self, market_data):
        """市場データを分析し、未来の市場予測スコアに基づき判断"""
        score = self.predict_market(market_data)

        if score > 0.6:
            decision = "BUY"
        elif score < 0.4:
            decision = "SELL"
        else:
            decision = "HOLD"

        self.logger.info(f"🔮 Prometheus: 予測スコア = {score:.4f} ➜ 決断: {decision}")
        return decision

    def predict_market(self, market_data):
        """MLPモデルによる未来市場スコア予測"""
        processed_data = self._preprocess_data(market_data)
        prediction = self.model.predict(processed_data, verbose=0)
        self.logger.info(f"📈 Prometheus予測: 入力 = {market_data}, 出力 = {prediction[0][0]:.4f}")
        return float(prediction)

    def _preprocess_data(self, market_data):
        """市場データの前処理（防御処理付き）"""
        if not isinstance(market_data, dict):
            self.logger.warning("⚠️ market_dataがlistなどで渡されたため空辞書に置換")
            market_data = {}

        return np.array([[
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
            1.0  # バイアス項
        ]])

# ✅ テスト用ブロック
if __name__ == "__main__":
    oracle = PrometheusOracle()
    mock_market_data = {
        "price": 1.2345, "volume": 1000, "sentiment": 0.8, "trend_strength": 0.7,
        "volatility": 0.15, "order_block": 0.6, "institutional_flow": 0.8,
        "short_interest": 0.5, "momentum": 0.9, "trend_prediction": 0.6,
        "liquidity_ratio": 1.2
    }
    forecast = oracle.predict_market(mock_market_data)
    print(f"🔮 Prometheusの市場予測スコア: {forecast:.4f}")
