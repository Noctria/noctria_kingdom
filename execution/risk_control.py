# risk_control.py
import math

class RiskControl:
    """
    Noctria Kingdom のリスク管理モジュール
    ----------------------------------------
    Fintokei の条件に合わせ、以下の制限ルールを実装しています。
      - 1日あたりの損失が5%を超えた場合、全ての取引を停止
      - 初期資本金に対して総損失が10%を超えた場合、全ての取引を停止

    また、各トレードにおけるリスク量をもとに、動的な注文ロットサイズの計算も行います。
    """

    def __init__(self, initial_capital: float, daily_loss_limit: float = 0.05, overall_loss_limit: float = 0.10):
        """
        コンストラクタ

        Parameters:
            initial_capital : システム運用開始時の資本金（例: 1,000,000 円）
            daily_loss_limit: 日次損失の上限割合（例: 0.05 は 5%）
            overall_loss_limit: 総損失の上限割合（例: 0.10 は 10%）
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.daily_start_capital = initial_capital  # 各取引日の開始時の資本金
        self.daily_loss_limit = daily_loss_limit
        self.overall_loss_limit = overall_loss_limit
        self.trade_active = True  # 取引継続フラグ

    def reset_daily(self):
        """
        新しい取引日の開始時に、日次の基準となる資本金を更新します。
        """
        self.daily_start_capital = self.current_capital
        self.trade_active = True

    def update_account(self, profit_loss: float):
        """
        取引の結果に基づいて現在資本金を更新します。

        Parameters:
            profit_loss: 取引の損益（正の値なら利益、負の値なら損失）
        """
        self.current_capital += profit_loss

    def check_risk(self):
        """
        現在の損失率（日次・総合）を計算し、リスク閾値を超えているかどうかを評価します。

        Returns:
            daily_loss_pct (float): 日次損失率
            overall_loss_pct (float): 初期資本金に対する総損失率
            trade_active (bool): 取引継続可能な場合 True、閾値超過時は False
        """
        if self.daily_start_capital > 0:
            daily_loss_pct = (self.daily_start_capital - self.current_capital) / self.daily_start_capital
        else:
            daily_loss_pct = 0.0

        overall_loss_pct = (self.initial_capital - self.current_capital) / self.initial_capital

        # 制限ルールを適用
        if daily_loss_pct >= self.daily_loss_limit or overall_loss_pct >= self.overall_loss_limit:
            self.trade_active = False
        else:
            self.trade_active = True

        return daily_loss_pct, overall_loss_pct, self.trade_active

    def calculate_order_size(self, stop_loss_distance: float, risk_per_trade: float = 0.01):
        """
        各トレードごとに、設定したリスク（資本金の何パーセントを失うか）に基づいて最適な注文サイズを計算します。

        Parameters:
            stop_loss_distance: ストップロスとなる価格差（単位は取り扱う通貨・商品の価格単位）
            risk_per_trade: 各トレードで許容するリスクの割合（例: 0.01 は 1%）

        Returns:
            order_size (float): 推奨される注文サイズ（理論値）
        """
        risk_amount = self.current_capital * risk_per_trade
        if stop_loss_distance <= 0:
            return 0  # 停止ロス距離が無効なら注文を控える
        order_size = risk_amount / stop_loss_distance
        return order_size

# ✅ シンプルなテストシミュレーション
if __name__ == "__main__":
    # 初期資本金 100万円を例として設定
    initial_capital = 1000000  
    risk_control = RiskControl(initial_capital)

    # 複数の取引結果をシミュレーション
    # ※各取引の結果は利益または損失（金額）
    trades = [10000, -20000, 5000, -50000, 30000, -100000]
    print("初期資本金:", initial_capital)
    for i, trade in enumerate(trades):
        risk_control.update_account(trade)
        daily_loss, overall_loss, active = risk_control.check_risk()
        print(f"取引 {i+1}: 損益 = {trade:+}, 現在資本金 = {risk_control.current_capital:.2f}, "
              f"日次損失率 = {daily_loss*100:.2f}%, 総損失率 = {overall_loss*100:.2f}% => 取引継続: {active}")
        if not active:
            print("【注意】リスク制限に達したため、取引を停止します。")
            break

    # 動的ロットサイズの計算例
    stop_loss_distance = 10  # 例：価格差 10 単位が損切り基準
    order_size = risk_control.calculate_order_size(stop_loss_distance)
    print(f"\nおすすめの注文サイズ（stop_loss_distance = {stop_loss_distance} に対して）: {order_size:.2f}")
