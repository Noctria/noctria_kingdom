import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

class RiskManager:
    """Noctria Kingdom のリスク管理モジュール"""

    # ❗️【修正点】historical_dataを必須引数からオプション引数に変更 (historical_data=None を追加)
    def __init__(self, historical_data=None):
        """
        初期化：リスク評価に使用する市場データをロード
        :param historical_data: pd.DataFrame (価格データ)
        """
        self.data = historical_data

        # ❗️【改善点】データが存在しない場合のエラーを防ぐ
        if self.data is None or self.data.empty or 'Close' not in self.data.columns:
            self.volatility = 0
            self.value_at_risk = np.inf # リスク無限大として扱う
        else:
            self.volatility = self.calculate_volatility()
            self.value_at_risk = self.calculate_var()

    def calculate_volatility(self):
        """市場ボラティリティの算出 (標準偏差ベース)"""
        if self.data is None or self.data.empty:
            return 0
        returns = np.log(self.data['Close'] / self.data['Close'].shift(1))
        return returns.std()

    def calculate_var(self, confidence_level=0.95):
        """VaR (Value at Risk) を計算"""
        if self.data is None or self.data.empty or len(self.data) < 2:
            return np.inf
        pct_changes = self.data['Close'].pct_change().dropna()
        if pct_changes.empty:
            return np.inf
        mean_return = np.mean(pct_changes)
        std_dev = np.std(pct_changes)
        # 修正: パーセンタイルは (1 - confidence_level) * 100 で計算
        return abs(mean_return - std_dev * np.percentile(pct_changes, (1 - confidence_level) * 100))

    def adjust_stop_loss(self, current_price):
        """市場のボラティリティに基づいてダイナミックにストップロスを調整"""
        if self.volatility == 0:
            return current_price * 0.95 # ボラティリティが計算できない場合は固定値
        stop_loss_level = current_price - (self.volatility * 2)
        return max(stop_loss_level, current_price * 0.95)  # 最低保証 5% 下限

    def detect_anomalies(self):
        """異常検知 (価格変動の異常を Holt-Winters モデルで確認)"""
        if self.data is None or len(self.data) < 20: # Holt-Wintersにはある程度のデータ点が必要
            return False
        model = ExponentialSmoothing(self.data['Close'], trend="add", seasonal=None)
        fitted_model = model.fit()
        residuals = self.data['Close'] - fitted_model.fittedvalues
        return residuals.abs().mean() > (2 * self.volatility)  # 2σ以上の異常値

    def optimal_position_size(self, capital, risk_per_trade=0.02):
        """ポジションサイズを最適化 (資本とリスク許容度に基づく)"""
        if self.value_at_risk is None or self.value_at_risk == 0 or np.isinf(self.value_at_risk):
            return 0 # リスクが計算できない場合はポジションを取らない
        return capital * risk_per_trade / self.value_at_risk

# ✅ テスト例（直接実行時）
if __name__ == "__main__":
    sample_data = pd.DataFrame({'Close': np.random.normal(loc=100, scale=5, size=100)})
    risk_manager = RiskManager(sample_data)

    print("📊 市場ボラティリティ:", risk_manager.volatility)
    print("📉 VaR:", risk_manager.value_at_risk)
    print("🛡️ ダイナミック・ストップロス:", risk_manager.adjust_stop_loss(102))
    print("🚨 異常検知:", risk_manager.detect_anomalies())
    print("📐 推奨ポジションサイズ（資本10000）:", risk_manager.optimal_position_size(10000))
    
    print("\n--- データなしで初期化テスト ---")
    risk_manager_no_data = RiskManager()
    print("📊 市場ボラティリティ (データなし):", risk_manager_no_data.volatility)
    print("📉 VaR (データなし):", risk_manager_no_data.value_at_risk)
