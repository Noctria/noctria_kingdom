import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing


class RiskManagement:
    """
    Noctria Kingdom のリスク管理モジュール
    - ボラティリティ、VaR、異常検知、ストップロス調整、ポジションサイズ算出を提供
    """

    def __init__(self, historical_data: pd.DataFrame):
        """
        :param historical_data: pd.DataFrame with at least 'Close' column
        """
        self.data = historical_data.copy()
        self._validate_data()

        self.volatility = self._calculate_volatility()
        self.value_at_risk = self._calculate_var()

    def _validate_data(self):
        if 'Close' not in self.data.columns:
            raise ValueError("❌ 'Close'列が必要です")
        if len(self.data) < 30:
            raise ValueError("❌ 過去データが30行以上必要です")

    def _calculate_volatility(self) -> float:
        """市場ボラティリティ（標準偏差ベースの対数リターン）"""
        returns = np.log(self.data['Close'] / self.data['Close'].shift(1)).dropna()
        return returns.std()

    def _calculate_var(self, confidence_level: float = 0.95) -> float:
        """VaR (Value at Risk) を計算（正規分布仮定の簡易版）"""
        pct_returns = self.data['Close'].pct_change().dropna()
        mean = pct_returns.mean()
        std = pct_returns.std()
        z_score = np.percentile(pct_returns, (1 - confidence_level) * 100)
        return abs(mean - z_score * std)

    def adjust_stop_loss(self, current_price: float) -> float:
        """
        市場ボラティリティに基づくダイナミック・ストップロス
        - 通常は価格の2σ下 + 最低5%下限で安全設計
        """
        stop_loss_level = current_price - (self.volatility * 2)
        return max(stop_loss_level, current_price * 0.95)

    def detect_anomalies(self) -> bool:
        """
        Holt-Wintersモデルを用いた価格変動の異常検出
        - 異常閾値: 平均残差 > 2σ
        """
        try:
            model = ExponentialSmoothing(self.data['Close'], trend="add", seasonal=None)
            fitted = model.fit()
            residuals = self.data['Close'] - fitted.fittedvalues
            mean_residual = residuals.abs().mean()
            return mean_residual > (2 * self.volatility)
        except Exception as e:
            print(f"⚠️ 異常検知失敗: {e}")
            return False

    def optimal_position_size(self, capital: float, risk_per_trade: float = 0.02) -> float:
        """
        資本と許容リスクに基づく推奨ポジションサイズ
        """
        if self.value_at_risk == 0:
            print("⚠️ VaRがゼロのためポジションサイズを計算できません")
            return 0.0
        return capital * risk_per_trade / self.value_at_risk


# ✅ 単体テスト
if __name__ == "__main__":
    np.random.seed(42)
    test_close = np.random.normal(loc=100, scale=5, size=100)
    sample_df = pd.DataFrame({'Close': test_close})

    rm = RiskManagement(sample_df)
    print("📊 市場ボラティリティ:", rm.volatility)
    print("💥 VaR:", rm.value_at_risk)
    print("🛡️ ストップロス(102):", rm.adjust_stop_loss(102))
    print("🚨 異常検知:", rm.detect_anomalies())
    print("📈 ポジションサイズ(資本10000):", rm.optimal_position_size(10000))
