# core/risk_control.py

import datetime
import pandas as pd

class RiskControl:
    """
    🛡️ Noctria Kingdom - 統合型リスク管理クラス
    - 日次損失制限、総損失制限、スキャルピング違反、マーチンゲール違反を検出
    """

    def __init__(self, initial_capital: float):
        self._capital = initial_capital
        self.daily_loss_limit = initial_capital * 0.05
        self.total_loss_limit = initial_capital * 0.10
        self.current_loss = 0.0
        self.last_trade_time = None
        self.last_reset_date = datetime.date.today()

    @property
    def current_capital(self) -> float:
        return self._capital

    def reset_daily_loss(self):
        """📅 新しい日付になったら日次損失カウンタをリセット"""
        today = datetime.date.today()
        if today > self.last_reset_date:
            self.current_loss = 0.0
            self.last_reset_date = today

    def update_account(self, profit_loss: float):
        """💰 損益を反映し、リスク閾値を再評価"""
        self._capital += profit_loss
        self.current_loss += profit_loss

    def check_risk(self, trade_time: pd.Timestamp) -> str:
        """
        リスクチェック関数
        - trade_time: 取引の発生時刻（pandas.Timestamp）

        戻り値:
        - "active": 取引継続OK
        - "blocked": リスク制限により取引停止
        """
        self.reset_daily_loss()

        # 🕒 スキャルピング違反（15秒以内）
        if self.last_trade_time and (trade_time - self.last_trade_time).total_seconds() < 15:
            return "blocked"

        # 📉 日次損失制限超過
        if self.current_loss < -self.daily_loss_limit:
            return "blocked"

        # 📉 総損失制限超過
        if self.current_loss < -self.total_loss_limit:
            return "blocked"

        # ✅ 問題なし
        self.last_trade_time = trade_time
        return "active"
