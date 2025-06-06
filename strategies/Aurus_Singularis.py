import numpy as np
import pandas as pd
import tensorflow as tf
from data.market_data_fetcher import MarketDataFetcher
from core.risk_management import RiskManagement

# ✅ GPU メモリの使用を制限（動的確保）
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
    except RuntimeError as e:
        print(f"GPU メモリ設定エラー: {e}")

class AurusSingularis:
    """市場トレンド分析と適応戦略設計を行うAI（MetaAI用改修版）"""

    def __init__(self):
        self._configure_gpu()
        self.model = self._build_model()
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

    def _configure_gpu(self):
        """✅ GPU メモリの使用を動的制限（重複登録を防ぐ）"""
        gpus = tf.config.list_physical_devices('GPU')
        if gpus:
            try:
                for gpu in gpus:
                    tf.config.experimental.set_memory_growth(gpu, True)
            except RuntimeError as e:
                print(f"GPU メモリ設定エラー: {e}")

    def _build_model(self):
        """MetaAI対応版の戦略モデル構築"""
        model = tf.keras.Sequential([
            tf.keras.layers.Input(shape=(12,)),
            tf.keras.layers.Dense(128, activation='relu'),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(1, activation='sigmoid')
        ])
        model.compile(optimizer='adam', loss='mse')
        return model

    def process(self, market_data):
        """
        市場データを分析し、Noctria AIとの戦略統合を適用
        ➜ 万一 market_data が list で渡された場合の防御対応
        """
        if not isinstance(market_data, dict):
            print("⚠️ market_dataがlistなどで渡されました。空辞書に置換します")
            market_data = {}

        processed_data = self._preprocess_data(market_data)
        prediction = self.model.predict(processed_data, verbose=0)

        if prediction > 0.6:
            return "BUY"
        elif prediction < 0.4:
            return "SELL"
        else:
            return "HOLD"

    def _preprocess_data(self, market_data):
        """
        市場データの前処理（改修版: トレンド強度・センチメント・流動性を考慮）
        ➜ キーが無い場合はデフォルト値(0.0)で堅牢化
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
            1  # バイアス項などの追加特徴量
        ]).reshape(1, -1)

# ✅ 改修後の市場戦略適用テスト
if __name__ == "__main__":
    aurus_ai = AurusSingularis()
    mock_market_data = {
        "price": 1.2345, "volume": 1000, "sentiment": 0.8, "trend_strength": 0.7,
        "volatility": 0.15, "order_block": 0.6, "institutional_flow": 0.8,
        "short_interest": 0.5, "momentum": 0.9, "trend_prediction": 0.6,
        "liquidity_ratio": 1.2
    }
    decision = aurus_ai.process(mock_market_data)
    print("Strategy Decision:", decision)
