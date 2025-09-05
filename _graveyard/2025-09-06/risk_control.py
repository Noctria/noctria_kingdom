# core/risk_control.py

import datetime
from typing import Tuple

class RiskControl:
    """
    🛡️ Noctria Kingdom - 統合型リスク管理クラス (v2.0)
    - 日次損失制限、総損失制限（ハイウォーターマーク方式）、スキャルピング違反、マーチンゲール違反を検出
    """

    def __init__(self, initial_capital: float, daily_loss_pct: float = 0.05, total_loss_pct: float = 0.10):
        # --- 基本設定 ---
        self._initial_capital = initial_capital
        self._current_capital = initial_capital
        self._high_water_mark = initial_capital  # ★修正点: 最高資産を記録

        # --- リスク許容額 (パーセンテージで保持) ---
        self.daily_loss_pct = daily_loss_pct
        self.total_loss_pct = total_loss_pct

        # --- 状態管理 ---
        self.current_daily_pnl = 0.0  # ★修正点: 変数名を明確化
        self.last_trade_time = None
        self.last_trade_size = 0.0
        self.last_trade_pnl = 0.0
        self.last_reset_date = datetime.date.today()
        
        # --- 違反検出設定 ---
        self.scalping_seconds_limit = 15

    @property
    def current_capital(self) -> float:
        """現在の総資産"""
        return self._current_capital

    @property
    def high_water_mark(self) -> float:
        """過去の最高資産額"""
        return self._high_water_mark

    @property
    def max_allowable_total_drawdown(self) -> float:
        """現在のハイウォーターマークに基づく、最大許容ドローダウン額"""
        return self._high_water_mark * self.total_loss_pct

    def _reset_daily_pnl_if_new_day(self):
        """📅 新しい日付になったら日次損益カウンタをリセット"""
        today = datetime.date.today()
        if today > self.last_reset_date:
            self.current_daily_pnl = 0.0
            self.last_reset_date = today

    def update_trade_result(self, profit_loss: float, trade_size: float, trade_time: datetime.datetime):
        """💰 1回の取引結果を反映し、状態を更新"""
        self._current_capital += profit_loss
        self.current_daily_pnl += profit_loss
        self.high_water_mark = max(self._high_water_mark, self._current_capital) # ★修正点: ハイウォーターマークを更新
        
        self.last_trade_pnl = profit_loss
        self.last_trade_size = trade_size
        self.last_trade_time = trade_time

    def pre_trade_check(self, new_trade_size: float, current_time: datetime.datetime) -> Tuple[bool, str]:
        """
        取引実行「前」に行うリスクチェック
        
        戻り値: (取引OKか, 理由) のタプル
        - (True, "active"): 取引継続OK
        - (False, "reason"): リスク制限により取引停止
        """
        self._reset_daily_pnl_if_new_day()

        # 📉 日次損失制限超過
        # ★修正点: 許容額を現在の資本ベースで動的に計算
        daily_loss_limit_value = self._current_capital * self.daily_loss_pct
        if self.current_daily_pnl < 0 and abs(self.current_daily_pnl) >= daily_loss_limit_value:
            return False, f"Daily loss limit exceeded: PnL({self.current_daily_pnl:.2f}) > Limit({daily_loss_limit_value:.2f})"

        # 📉 総損失制限超過 (ドローダウン)
        # ★修正点: 最高資産からのドローダウンで評価
        current_drawdown = self.high_water_mark - self._current_capital
        if current_drawdown > 0 and current_drawdown >= self.max_allowable_total_drawdown:
            return False, f"Total drawdown limit exceeded: DD({current_drawdown:.2f}) > Limit({self.max_allowable_total_drawdown:.2f})"

        # 🎰 マーチンゲール違反
        # ★追加: 損失が出た直後にロットサイズを上げたかをチェック
        if self.last_trade_pnl < 0 and new_trade_size > self.last_trade_size:
            return False, f"Martingale violation detected: NewSize({new_trade_size}) > LastSize({self.last_trade_size}) after loss"

        # 🕒 スキャルピング違反
        if self.last_trade_time and (current_time - self.last_trade_time).total_seconds() < self.scalping_seconds_limit:
            return False, f"Scalping violation: Time since last trade < {self.scalping_seconds_limit}s"

        # ✅ 問題なし
        return True, "active"

# ✅ 動作確認用
if __name__ == "__main__":
    rc = RiskControl(initial_capital=100000)
    print(f"初期資産: {rc.current_capital}, 日次許容損失: {rc._current_capital * rc.daily_loss_pct}, 総許容DD: {rc.max_allowable_total_drawdown}")

    # 取引前のチェック
    is_ok, reason = rc.pre_trade_check(new_trade_size=1.0, current_time=datetime.datetime.now())
    print(f"初回取引チェック: OK? {is_ok}, 理由: {reason}")
    
    # 負け取引を記録
    rc.update_trade_result(profit_loss=-6000, trade_size=1.0, trade_time=datetime.datetime.now())
    print(f"6000円損失後 -> 資産: {rc.current_capital}, 日次損益: {rc.current_daily_pnl}, 最高資産: {rc.high_water_mark}")

    # 日次損失超過のチェック
    is_ok, reason = rc.pre_trade_check(new_trade_size=1.0, current_time=datetime.datetime.now() + datetime.timedelta(minutes=1))
    print(f"日次損失超過チェック: OK? {is_ok}, 理由: {reason}")
    
    # マーチンゲール違反のチェック
    is_ok, reason = rc.pre_trade_check(new_trade_size=1.1, current_time=datetime.datetime.now() + datetime.timedelta(minutes=2))
    print(f"マーチンゲール違反チェック: OK? {is_ok}, 理由: {reason}")
