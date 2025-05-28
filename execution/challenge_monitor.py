# challenge_monitor.py
import time
# ※実際の環境では smtplib などを利用してメールを送るなどのアラート機能を実装できます
from email.mime.text import MIMEText
import smtplib

class ChallengeMonitor:
    """
    フィントケイ用チャレンジ進捗モニタリング・アラート機能
    リスク管理モジュール（RiskControl）と連携して、
    1日損失率や総損失率が事前の閾値に近づいた場合にアラートを発する仕組みです。
    """
    def __init__(self, risk_control, alert_threshold_daily=0.045, alert_threshold_overall=0.09):
        self.risk_control = risk_control
        self.alert_threshold_daily = alert_threshold_daily
        self.alert_threshold_overall = alert_threshold_overall

    def monitor(self):
        """
        リスク状況をチェックし、閾値に達している場合はアラートを発信。
        戻り値として現在のリスク状態を返します。
        """
        daily_loss, overall_loss, active = self.risk_control.check_risk()
        if daily_loss >= self.alert_threshold_daily:
            self.send_alert("日次損失閾値超え注意", daily_loss)
        if overall_loss >= self.alert_threshold_overall:
            self.send_alert("総損失閾値超え注意", overall_loss)
        return daily_loss, overall_loss, active

    def send_alert(self, subject, value):
        """
        実際のアラート送信動作（ここでは print でシミュレーション）。
        ここに SMTP を使ったメール送信や、チャットツールとの連携機能などを追加できます。
        """
        message = f"{subject}: 現在の値は {value:.2%} です。システム状況の確認をお願いします！"
        print("ALERT:", message)

        # 例：メール送信（必要に応じて設定）
        # msg = MIMEText(message)
        # msg['Subject'] = subject
        # msg['From'] = 'alert@example.com'
        # msg['To'] = 'user@example.com'
        # with smtplib.SMTP('smtp.example.com') as server:
        #     server.login('username', 'password')
        #     server.send_message(msg)


# テスト運用用
if __name__ == "__main__":
    from risk_control import RiskControl
    import numpy as np

    # 初期資本金 100万円の RiskControl インスタンスを生成
    risk_control = RiskControl(initial_capital=1000000)
    # 仮のシナリオ：現在資本金をシミュレーションで下げる（例：90万円）
    risk_control.current_capital = 900000  # 10%の損失になり十分に警戒すべき状態

    monitor = ChallengeMonitor(risk_control)
    daily, overall, active = monitor.monitor()
    print(f"日次損失率: {daily:.2%}, 総損失率: {overall:.2%}, 取引継続: {active}")
