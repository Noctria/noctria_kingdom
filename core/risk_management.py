import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

class RiskManagement:
    """Noctria Kingdom のリスク管理モジュール"""

    def __init__(self, historical_data):
        """
        初期化：リスク評価に使用する市場データをロード
        :param historical_data: pd.DataFrame (価格データ)
        """
        self.data = historical_data
        self.volatility = self.calculate_volatility()
        self.value_at_risk = self.calculate_var()

    def calculate_volatility(self):
        """市場ボラティリティの算出 (標準偏差ベース)"""
        returns = np.log(self.data['Close'] / self.data['Close'].shift(1))
        return returns.std()

    def calculate_var(self, confidence_level=0.95):
        """VaR (Value at Risk) を計算"""
        mean_return = np.mean(self.data['Close'].pct_change())
        std_dev = np.std(self.data['Close'].pct_change())
        return mean_return - std_dev * np.percentile(self.data['Close'].pct_change(), confidence_level * 100)

    def adjust_stop_loss(self, current_price):
        """市場のボラティリティに基づいてダイナミックにストップロスを調整"""
        stop_loss_level = current_price - (self.volatility * 2)
        return max(stop_loss_level, current_price * 0.95)  # 最低保証 5% 下限

    def detect_anomalies(self):
        """異常検知 (価格変動の異常を Holt-Winters モデルで確認)"""
        model = ExponentialSmoothing(self.data['Close'], trend="add", seasonal=None)
        fitted_model = model.fit()
        residuals = self.data['Close'] - fitted_model.fittedvalues
        return residuals.abs().mean() > (2 * self.volatility)  # 2σ以上の異常値

    def optimal_position_size(self, capital, risk_per_trade=0.02):
        """ポジションサイズを最適化 (資本とリスク許容度に基づく)"""
        return capital * risk_per_trade / self.value_at_risk

# テストデータの例
if __name__ == "__main__":
    sample_data = pd.DataFrame({'Close': np.random.normal(loc=100, scale=5, size=100)})
    risk_manager = RiskManagement(sample_data)

    print("市場ボラティリティ:", risk_manager.volatility)
    print("VaR:", risk_manager.value_at_risk)
    print("ダイナミック・ストップロス:", risk_manager.adjust_stop_loss(102))
    print("異常検知:", risk_manager.detect_anomalies())
    print("推奨ポジションサイズ (資本10000):", risk_manager.optimal_position_size(10000))
