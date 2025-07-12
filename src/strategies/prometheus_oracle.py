import numpy as np
import tensorflow as tf
import pandas as pd
from datetime import datetime, timedelta
from sklearn.metrics import mean_squared_error, mean_absolute_error

from core.data_loader import MarketDataFetcher
from core.risk_manager import RiskManager
from core.settings import ALPHAVANTAGE_API_KEY


class PrometheusOracle:
    """
    📈 市場予測を行うAIモデル
    - 実データ（日足）に基づいた予測
    - 信頼区間付き日次予測に対応
    - ✅ RiskManager はオプション（将来の拡張用）
    """

    def __init__(self, use_risk: bool = False):
        self.model = self._build_model()
        self.market_fetcher = MarketDataFetcher(api_key=ALPHAVANTAGE_API_KEY)
        self.risk_manager = None

        if use_risk:
            df = self.market_fetcher.fetch_daily_data(from_symbol="USD", to_symbol="JPY", max_days=90)
            if df is not None and not df.empty:
                self.risk_manager = RiskManager(df)

    def _build_model(self):
        """
        📐 簡易予測モデル（単変量回帰）
        将来的には LSTM / Transformer に差し替え可能
        """
        model = tf.keras.Sequential([
            tf.keras.layers.Dense(128, activation='relu', input_shape=(1,)),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(1, activation='linear')
        ])
        model.compile(optimizer='adam', loss='mse')
        return model

    def predict_with_confidence(self, n_days: int = 14) -> pd.DataFrame:
        """
        🔮 実データ（日次終値）に基づいた予測＋信頼区間
        """
        df = self.market_fetcher.fetch_daily_data(from_symbol="USD", to_symbol="JPY", max_days=90)
        if df.empty or len(df) < 10:
            raise ValueError("為替日次データの取得に失敗、またはデータ不足")

        df = df.sort_values("date")
        df["days"] = (df["date"] - df["date"].min()).dt.days
        X = df[["days"]].values
        y = df["close"].values

        # モデル学習
        self.model.fit(X, y, epochs=50, verbose=0)

        # 未来の日数生成
        last_day = df["days"].max()
        future_days = np.arange(last_day + 1, last_day + 1 + n_days).reshape(-1, 1)
        preds = self.model.predict(future_days).flatten()

        # 信頼区間推定（標準偏差ベース）
        residuals = y - self.model.predict(X).flatten()
        std_dev = np.std(residuals)

        future_dates = [df["date"].max() + timedelta(days=i + 1) for i in range(n_days)]
        records = []
        for i in range(n_days):
            pred = preds[i]
            records.append({
                "date": future_dates[i].strftime("%Y-%m-%d"),
                "y_pred": round(pred, 4),
                "y_lower": round(pred - std_dev, 4),
                "y_upper": round(pred + std_dev, 4)
            })

        return pd.DataFrame(records)

    def evaluate_model(self, n_days: int = 14) -> dict:
        """
        🧪 モデルの精度評価（直近n日分）
        - 指標: RMSE, MAE, MAPE
        """
        df = self.market_fetcher.fetch_daily_data(from_symbol="USD", to_symbol="JPY", max_days=90)
        if df.empty or len(df) < n_days + 10:
            raise ValueError("評価に必要な過去データが不足しています")

        df = df.sort_values("date")
        df["days"] = (df["date"] - df["date"].min()).dt.days

        X = df[["days"]].values
        y = df["close"].values

        # モデル再学習
        self.model.fit(X, y, epochs=50, verbose=0)

        X_val = X[-n_days:]
        y_true = y[-n_days:]
        y_pred = self.model.predict(X_val).flatten()

        rmse = mean_squared_error(y_true, y_pred, squared=False)
        mae = mean_absolute_error(y_true, y_pred)
        mape = np.mean(np.abs((y_true - y_pred) / np.clip(y_true, 1e-6, None))) * 100

        return {
            "RMSE": round(rmse, 4),
            "MAE": round(mae, 4),
            "MAPE": round(mape, 2),
        }
