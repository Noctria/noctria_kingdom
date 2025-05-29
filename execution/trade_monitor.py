import datetime

class TradeMonitor:
    def __init__(self):
        self.last_trade_date = None

    def update_trade(self, trade_date):
        self.last_trade_date = trade_date

    def check_trade_activity(self):
        """ 30日間無トレードの失格防止 """
        if self.last_trade_date:
            days_since_last_trade = (datetime.datetime.now() - self.last_trade_date).days
            if days_since_last_trade >= 30:
                return "Warning: No trades in the last 30 days!"
        return "Trade activity is normal."

trade_monitor = TradeMonitor()
trade_monitor.update_trade(datetime.datetime.now() - datetime.timedelta(days=29))
print(trade_monitor.check_trade_activity())
