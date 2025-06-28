import pandas as pd
import datetime

class RiskManager:
    def __init__(self, balance):
        self.balance = balance
        self.daily_loss_limit = balance * 0.05
        self.total_loss_limit = balance * 0.10
        self.current_loss = 0
        self.last_trade_time = None
        self.last_reset_date = datetime.date.today()

    def reset_daily_loss(self):
        """ 日次損失リセット """
        today = datetime.date.today()
        if today > self.last_reset_date:
            self.current_loss = 0
            self.last_reset_date = today

    def check_risk(self, trade_amount, trade_result, trade_time):
        """ フィントケイの失格ルールを考慮したリスク管理 """

        self.reset_daily_loss()

        # スキャルピング禁止（15秒以内）
        if self.last_trade_time and (trade_time - self.last_trade_time).seconds < 15:
            return "Trade Rejected: Scalping Violation"

        # マーチンゲール禁止（損失時にロット増加不可）
        if trade_result < 0 and trade_amount > self.daily_loss_limit * 0.5:
            return "Trade Rejected: Martingale Violation"

        # 最大損失制限
        self.current_loss += trade_result
        if self.current_loss < -self.daily_loss_limit:
            return "Trade Rejected: Daily Loss Limit Exceeded"
        if self.current_loss < -self.total_loss_limit:
            return "Trade Rejected: Total Loss Limit Exceeded"

        # 取引時間を更新
        self.last_trade_time = trade_time

        return "Trade Approved"

# 使用例
risk_manager = RiskManager(balance=10000)
print(risk_manager.check_risk(trade_amount=200, trade_result=-500, trade_time=pd.Timestamp.now()))
