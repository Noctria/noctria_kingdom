import MetaTrader5 as mt5

class RiskControl:
    """ストップロス・資金管理を統括するモジュール"""

    def __init__(self, risk_limit=2.0):
        self.risk_limit = risk_limit

    def assess_risk(self):
        """口座のドローダウンをチェック"""
        balance = mt5.account_info().balance
        equity = mt5.account_info().equity
        drawdown = ((balance - equity) / balance) * 100
        return drawdown

    def enforce_risk_rules(self):
        """リスク閾値を超えたら注文制限"""
        drawdown = self.assess_risk()
        return "Trading restricted" if drawdown > self.risk_limit else "Safe to trade"

# ✅ リスク評価テスト
if __name__ == "__main__":
    risk_manager = RiskControl()
    risk_status = risk_manager.enforce_risk_rules()
    print("Risk Assessment:", risk_status)
