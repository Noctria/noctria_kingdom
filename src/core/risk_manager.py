import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from scipy.stats import norm
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

class RiskManager:
    """Noctria Kingdom のリスク管理モジュール"""

    def __init__(self, historical_data=None):
        """
        初期化：リスク評価に使用する市場データをロード
        :param historical_data: pd.DataFrame (価格データ, 'Close'列が必要)
        """
        self.data = historical_data

        if self.data is None or self.data.empty or 'Close' not in self.data.columns:
            logging.warning("【RiskManager初期化】リスク計算に必要なデータ（'Close'列）が欠損しています。")
            self.volatility = 0
            self.value_at_risk = np.inf
        else:
            self.volatility = self.calculate_volatility()
            self.value_at_risk = self.calculate_var()

    def calculate_volatility(self):
        """市場ボラティリティの算出 (標準偏差ベース, 対数リターン)"""
        if self.data is None or self.data.empty or 'Close' not in self.data.columns:
            logging.warning("【RiskManager】ボラティリティ算出時にデータが欠損しています。")
            return 0
        returns = np.log(self.data['Close'] / self.data['Close'].shift(1)).dropna()
        return returns.std()

    def calculate_var(self, confidence_level=0.95):
        """
        VaR (Value at Risk) を正規分布前提で計算
        金融実務でよく使われる「右側信頼区間」基準。
        - z_score = norm.ppf(confidence_level)
        - 損失側リスクは負方向なので -(mean + z*std)
        - VaRは損失額として正値のみ返す
        """
        if self.data is None or self.data.empty or len(self.data) < 2:
            logging.warning("【RiskManager】VaR算出時に十分なデータがありません。")
            return np.inf
        if 'Close' not in self.data.columns:
            logging.warning("【RiskManager】VaR算出時に必要な'Close'カラムがありません。")
            return np.inf
        pct_changes = self.data['Close'].pct_change().dropna()
        if pct_changes.empty:
            logging.warning("【RiskManager】VaR算出時、リターン系列が空です。")
            return np.inf
        mean_return = np.mean(pct_changes)
        std_dev = np.std(pct_changes)
        z_score = norm.ppf(confidence_level)
        var = -(mean_return + z_score * std_dev)
        return max(var, 0.0)

    def calculate_var_ratio(self, price, confidence_level=0.95):
        """
        VaRリスク値を「現価格比」で返す（Noctus等で使う）
        """
        var = self.calculate_var(confidence_level)
        if price == 0 or np.isinf(var):
            return 1.0
        return var / price

    def adjust_stop_loss(self, current_price):
        """市場ボラティリティに応じてストップロス値を調整"""
        if self.volatility == 0:
            return current_price * 0.95
        stop_loss_level = current_price - (self.volatility * 2)
        return max(stop_loss_level, current_price * 0.95)

    def detect_anomalies(self):
        """
        異常検知 (Holt-Winters平滑法)
        戻り値: (異常あり: bool, 異常リスト: list)
        """
        if self.data is None or len(self.data) < 20 or 'Close' not in self.data.columns:
            logging.warning("【RiskManager】異常検知に必要なデータが不足しています。")
            return False, []
        try:
            model = ExponentialSmoothing(self.data['Close'], trend="add", seasonal=None)
            fitted_model = model.fit()
            residuals = self.data['Close'] - fitted_model.fittedvalues
            anomalies = self.data[residuals.abs() > (2 * self.volatility)]
            is_anomaly = len(anomalies) > 0
            return is_anomaly, anomalies.index.tolist()
        except Exception as e:
            logging.error(f"異常検知中にエラー: {e}")
            return False, []

    def optimal_position_size(self, capital, risk_per_trade=0.02):
        """ポジションサイズ最適化（資本とリスク許容度）"""
        if self.value_at_risk is None or self.value_at_risk == 0 or np.isinf(self.value_at_risk):
            logging.warning("【RiskManager】ポジションサイズ計算時、VaR値が無効です。")
            return 0
        return capital * risk_per_trade / self.value_at_risk

# ✅ テスト例
if __name__ == "__main__":
    sample_data = pd.DataFrame({'Close': np.random.normal(loc=100, scale=5, size=100)})
    risk_manager = RiskManager(sample_data)

    print("📊 市場ボラティリティ:", risk_manager.volatility)
    print("📉 VaR:", risk_manager.value_at_risk)
    print("📉 VaR比率:", risk_manager.calculate_var_ratio(102))
    print("🛡️ ダイナミック・ストップロス:", risk_manager.adjust_stop_loss(102))
    is_anom, anom_idx = risk_manager.detect_anomalies()
    print("🚨 異常検知:", is_anom, "異常index:", anom_idx)
    print("📐 推奨ポジションサイズ（資本10000）:", risk_manager.optimal_position_size(10000))

    print("\n--- データなしで初期化テスト ---")
    risk_manager_no_data = RiskManager()
    print("📊 市場ボラティリティ (データなし):", risk_manager_no_data.volatility)
    print("📉 VaR (データなし):", risk_manager_no_data.value_at_risk)
