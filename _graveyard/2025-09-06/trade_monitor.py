import datetime
import os
import pandas as pd
import MetaTrader5 as mt5
from core.Noctria import Noctria


class TradeMonitor:
    def __init__(self):
        self.last_trade_date = None

    def update_trade(self, trade_date):
        self.last_trade_date = trade_date

    def check_trade_activity(self):
        """ 30日間無トレードの失格防止チェック """
        if self.last_trade_date:
            days_since = (datetime.datetime.now() - self.last_trade_date).days
            if days_since >= 30:
                return "Warning: No trades in the last 30 days!"
        return "Trade activity is normal."

    def save_trade_history_and_feedback(self):
        """
        直近1週間の取引履歴を取得し、CSVに保存。
        さらに Noctria AI へフィードバックを渡す。
        """
        today = datetime.date.today()
        start_date = today - datetime.timedelta(days=7)
        end_date = today

        print(f"[INFO] Getting trade history: {start_date} to {end_date}")

        if not mt5.initialize():
            print("[ERROR] MT5 initialization failed.")
            return

        deals = mt5.history_deals_get(start_date, end_date)
        mt5.shutdown()

        if deals is None:
            print("[INFO] No trade history found.")
            return

        df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
        os.makedirs("logs", exist_ok=True)
        file_name = f"logs/trade_history_{start_date}_to_{end_date}.csv"
        df.to_csv(file_name, index=False)
        print(f"[INFO] Trade history saved to {file_name}")

        # ✅ Noctria AI へフィードバック
        noctria_ai = Noctria()
        feedback = noctria_ai.feedback_trade_results(df)
        print("[フィードバック結果]", feedback)


# ✅ テスト実行例
if __name__ == "__main__":
    trade_monitor = TradeMonitor()
    trade_monitor.update_trade(datetime.datetime.now() - datetime.timedelta(days=29))
    print(trade_monitor.check_trade_activity())

    # 🔥 取引履歴の取得・保存・AIフィードバック
    trade_monitor.save_trade_history_and_feedback()
