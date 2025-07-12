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
    🔮 未来予測を担うAI「Prometheus」
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
        model = tf.keras.Sequential([
            tf.keras.layers.Dense(128, activation='relu', input_shape=(1,)),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(1, activation='linear')
        ])
        model.compile(optimizer='adam', loss='mse')
        return model

    def predict_with_confidence(self, n_days: int = 14) -> pd.DataFrame:
        df = self.market_fetcher.fetch_daily_data(from_symbol="USD", to_symbol="JPY", max_days=90)
        if df.empty or len(df) < 10:
            raise ValueError("為替日次データの取得に失敗、またはデータ不足")

        df = df.sort_values("date")
        df["days"] = (df["date"] - df["date"].min()).dt.days
        X = df[["days"]].values
        y = df["close"].values

        self.model.fit(X, y, epochs=50, verbose=0)

        last_day = df["days"].max()
        future_days = np.arange(last_day + 1, last_day + 1 + n_days).reshape(-1, 1)
        preds = self.model.predict(future_days).flatten()

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
        df = self.market_fetcher.fetch_daily_data(from_symbol="USD", to_symbol="JPY", max_days=90)
        if df.empty or len(df) < n_days + 10:
            raise ValueError("評価に必要な過去データが不足しています")

        df = df.sort_values("date")
        df["days"] = (df["date"] - df["date"].min()).dt.days

        X = df[["days"]].values
        y = df["close"].values

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

    def propose(self, n_days: int = 3) -> dict:
        """
        📩 王Noctriaへの献上：予測情報を簡易サマリーとして提供
        """
        try:
            df_forecast = self.predict_with_confidence(n_days=n_days)
            latest = df_forecast.iloc[0]

            score = round(latest["y_pred"], 4)
            lower = round(latest["y_lower"], 4)
            upper = round(latest["y_upper"], 4)

            # 上昇見込み or 下降見込みの判定
            direction = "BUY" if lower > latest["y_pred"] else "SELL" if upper < latest["y_pred"] else "HOLD"

            return {
                "name": "Prometheus",
                "type": "forecasting",
                "signal": direction,
                "score": score,
                "confidence": {"lower": lower, "upper": upper},
                "symbol": "USDJPY",
                "priority": "future"
            }

        except Exception as e:
            print(f"[Prometheus] ❌ 提案生成失敗: {e}")
            return {
                "name": "Prometheus",
                "type": "forecasting",
                "signal": "UNKNOWN",
                "score": 0.0,
                "symbol": "USDJPY",
                "priority": "future"
            }


# ✅ 単体テスト
if __name__ == "__main__":
    oracle = PrometheusOracle()
    result = oracle.propose()
    print("📈 未来予測提案:", result)
