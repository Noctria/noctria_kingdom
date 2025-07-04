# core/risk_control.py

import datetime
import pandas as pd

class RiskManager:
    """
    Noctria Kingdom - 統合型リスク管理クラス
    - 日次損失制限、総損失制限、スキャルピング違反、マーチンゲール違反を検出
    """

    def __init__(self, balance: float):
        self.balance = balance
        self.daily_loss_limit = balance * 0.05
        self.total_loss_limit = balance * 0.10
        self.current_loss = 0.0
        self.last_trade_time = None
        self.last_reset_date = datetime.date.today()

    def reset_daily_loss(self):
        """ 📅 新しい日付になったら日次損失カウンタをリセット """
        today = datetime.date.today()
        if today > self.last_reset_date:
            self.current_loss = 0.0
            self.last_reset_date = today

    def check_risk(self, trade_amount: float, trade_result: float, trade_time: pd.Timestamp) -> str:
        """
        リスクチェック関数
        - trade_amount: 今回の取引金額
        - trade_result: 今回の損益（利益なら＋、損失なら−）
        - trade_time: 取引の発生時刻（pandas.Timestamp）
        """

        self.reset_daily_loss()

        # 🕒 スキャルピング禁止（15秒以内の連続取引）
        if self.last_trade_time and (trade_time - self.last_trade_time).total_seconds() < 15:
            return "❌ Trade Rejected: Scalping Violation"

        # 📉 マーチンゲール禁止（損失直後に取引額を急増させる）
        if trade_result < 0 and trade_amount > self.daily_loss_limit * 0.5:
            return "❌ Trade Rejected: Martingale Violation"

        # 📉 最大損失制限チェック
        self.current_loss += trade_result
        if self.current_loss < -self.daily_loss_limit:
            return "❌ Trade Rejected: Daily Loss Limit Exceeded"
        if self.current_loss < -self.total_loss_limit:
            return "❌ Trade Rejected: Total Loss Limit Exceeded"

        # ✅ 取引が承認された場合は時刻を記録
        self.last_trade_time = trade_time
        return "✅ Trade Approved"
