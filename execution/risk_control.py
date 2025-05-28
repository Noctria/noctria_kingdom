# risk_control.py (一部改良例)
import math
import numpy as np

class RiskControl:
    """
    リスク管理モジュール（Fintokei のルール: 日次 5%、総損失 10%）
    さらに、動的調整機能を導入して市場ボラティリティに応じた閾値の調整を可能にします。
    """
    def __init__(self, initial_capital: float, daily_loss_limit: float = 0.05, overall_loss_limit: float = 0.10):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.daily_start_capital = initial_capital
        self.base_daily_loss_limit = daily_loss_limit  # 基本値
        self.base_overall_loss_limit = overall_loss_limit  # 基本値
        self.daily_loss_limit = daily_loss_limit  # 調整後の値
        self.overall_loss_limit = overall_loss_limit  # 調整後の値
        self.trade_active = True
        self.dynamic_adjustment_factor = 1.0  # 市場の状態に応じた調整係数

    def adjust_risk_parameters(self, recent_prices, window: int = 20):
        """
        直近の市場データからボラティリティを計算し、
        リスクパラメータ（損失閾値）の動的調整を行います。
        
        Parameters:
          recent_prices: 直近の価格データの配列（例：過去20営業日の終値）
          window: 期間（デフォルトは20日）
        """
        if len(recent_prices) < window:
            # 十分なデータがない場合は何も変更しない
            self.dynamic_adjustment_factor = 1.0
        else:
            # 日次のリターンを計算
            returns = np.diff(np.log(recent_prices[-window:]))
            volatility = np.std(returns)
            
            # 例として、標準値 0.01（1%）を基準に調整し、volatility が 1% を超えたら係数を下げる
            if volatility > 0.01:
                self.dynamic_adjustment_factor = 0.8  # 安全側にシフト
            else:
                self.dynamic_adjustment_factor = 1.0

        # 調整後のリスク許容値を更新
        self.daily_loss_limit = self.base_daily_loss_limit * self.dynamic_adjustment_factor
        self.overall_loss_limit = self.base_overall_loss_limit * self.dynamic_adjustment_factor

    def reset_daily(self):
        self.daily_start_capital = self.current_capital
        self.trade_active = True

    def update_account(self, profit_loss: float):
        self.current_capital += profit_loss

    def check_risk(self):
        if self.daily_start_capital > 0:
            daily_loss_pct = (self.daily_start_capital - self.current_capital) / self.daily_start_capital
        else:
            daily_loss_pct = 0.0

        overall_loss_pct = (self.initial_capital - self.current_capital) / self.initial_capital

        # 調整後の閾値に基づいてチェック
        if daily_loss_pct >= self.daily_loss_limit or overall_loss_pct >= self.overall_loss_limit:
            self.trade_active = False
        else:
            self.trade_active = True

        return daily_loss_pct, overall_loss_pct, self.trade_active

    def calculate_order_size(self, stop_loss_distance: float, risk_per_trade: float = 0.01):
        risk_amount = self.current_capital * risk_per_trade
        if stop_loss_distance <= 0:
            return 0
        order_size = risk_amount / stop_loss_distance
        return order_size

# シンプルなテスト用スクリプト（実際のシミュレーションに組み込む前に確認）
if __name__ == "__main__":
    initial_capital = 1000000
    risk_control = RiskControl(initial_capital)
    
    # 仮の直近20営業日分の価格データ生成
    np.random.seed(42)
    recent_prices = 100 * np.cumprod(1 + np.random.normal(0, 0.01, 20))
    
    # 動的リスク調整の実行
    risk_control.adjust_risk_parameters(recent_prices)
    print(f"動的調整係数: {risk_control.dynamic_adjustment_factor}")
    print(f"調整後の日次損失許容値: {risk_control.daily_loss_limit*100:.2f}%")
    print(f"調整後の総損失許容値: {risk_control.overall_loss_limit*100:.2f}%")
