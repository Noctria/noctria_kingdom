import numpy as np
import pandas as pd
import tensorflow as tf
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

from core.data_loader import MarketDataFetcher
from core.settings import ALPHAVANTAGE_API_KEY


class PrometheusOracle:
    def __init__(self):
        self.model = self._build_model()
        self.market_fetcher = MarketDataFetcher(api_key=ALPHAVANTAGE_API_KEY)

    def _build_model(self):
        model = tf.keras.Sequential([
            tf.keras.layers.Dense(64, activation='relu', input_shape=(30,)),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(1)
        ])
        model.compile(optimizer='adam', loss='mse')
        return model

    def predict(self, n_days: int = 30) -> pd.DataFrame:
        """固定日数による予測"""
        dates = [datetime.today() + timedelta(days=i) for i in range(n_days)]
        y_pred = np.linspace(150, 160, n_days) + np.random.normal(0, 1, n_days)
        y_lower = y_pred - np.random.uniform(1, 2, n_days)
        y_upper = y_pred + np.random.uniform(1, 2, n_days)
        y_true = y_pred + np.random.normal(0, 2, n_days)  # ✅ 仮の実測値

        return pd.DataFrame({
            "date": [d.strftime("%Y-%m-%d") for d in dates],
            "y_pred": y_pred.round(2),
            "y_lower": y_lower.round(2),
            "y_upper": y_upper.round(2),
            "y_true": y_true.round(2),  # ✅ 追加
        })

    def predict_with_confidence(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        n_days: Optional[int] = 14
    ) -> pd.DataFrame:
        """日付範囲指定対応の予測メソッド（GUI連携用）"""
        try:
            if from_date:
                start_date = datetime.strptime(from_date, "%Y-%m-%d")
            else:
                start_date = datetime.today()

            if to_date:
                end_date = datetime.strptime(to_date, "%Y-%m-%d")
            else:
                end_date = start_date + timedelta(days=n_days - 1)

            # 日付の正規化
            if end_date < start_date:
                start_date, end_date = end_date, start_date

            n_days_calc = (end_date - start_date).days + 1
            dates = [start_date + timedelta(days=i) for i in range(n_days_calc)]

            # 🔮 ダミー予測（将来はモデルに置換）
            y_pred = np.linspace(150, 160, n_days_calc) + np.random.normal(0, 1, n_days_calc)
            y_lower = y_pred - np.random.uniform(1, 2, n_days_calc)
            y_upper = y_pred + np.random.uniform(1, 2, n_days_calc)
            y_true = y_pred + np.random.normal(0, 2, n_days_calc)  # ✅ 仮の実測値

            return pd.DataFrame({
                "date": [d.strftime("%Y-%m-%d") for d in dates],
                "forecast": y_pred.round(2),
                "lower": y_lower.round(2),
                "upper": y_upper.round(2),
                "y_true": y_true.round(2),  # ✅ 追加
            })

        except Exception as e:
            print(f"🔴 日付指定付き予測エラー: {e}")
            raise

    def evaluate_model(self, data: pd.DataFrame) -> dict:
        """
        モデルの予測結果を評価するメソッド
        ここでは、RMSE（平均二乗誤差平方根）とMSEを計算します。
        """
        try:
            y_true = data['y_true']
            # predict_with_confidenceを使う場合は 'forecast' キーを利用
            y_pred = data.get('y_pred') if 'y_pred' in data else data.get('forecast')

            if y_pred is None:
                raise KeyError("データフレームに 'y_pred' または 'forecast' 列がありません")

            mse = np.mean((y_true - y_pred) ** 2)
            rmse = np.sqrt(mse)

            return {
                'MSE': mse,
                'RMSE': rmse
            }
        except Exception as e:
            print(f"🔴 モデル評価エラー: {e}")
            raise


# ✅ GUIから呼び出し用ユーティリティ
def predict_and_save(output_path: Path, n_days: int = 30):
    oracle = PrometheusOracle()
    df = oracle.predict(n_days=n_days)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_json(output_path, orient="records", force_ascii=False)
