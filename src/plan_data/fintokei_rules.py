# ruff: noqa
# coding: utf-8
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class RuleViolation:
    code: str
    message: str
    details: Dict = field(default_factory=dict)
    severity: str = "ERROR"  # ERROR | WARN | INFO


@dataclass
class RuleResult:
    ok: bool
    violations: List[RuleViolation] = field(default_factory=list)


class FintokeiRuleEnforcer:
    """
    Fintokeiルール（要約版）を機械チェックする簡易ガード。
    - サファイアプラン前提の上限チェック
    - ギャンブル的行為の素朴なヒューリスティック
    """

    def __init__(self, plan_config: Optional[Dict] = None):
        # デフォルト：plan_sapphire
        default = {
            "initial_capital": 200_000,
            "max_risk_per_trade_pct": 5.0,
            "max_daily_dd_pct": 5.0,
            "max_total_dd_pct": 10.0,
        }
        self.cfg = {**default, **(plan_config or {})}

    def _calc_risk_amount(
        self, entry: float, sl: float, lot: float, contract_size: float = 100_000
    ) -> float:
        # FX想定の単純計算：価格差 × ロット × 取引単位
        return abs(entry - sl) * lot * contract_size

    def check_max_risk(
        self, capital: float, entry: float, sl: float, lot: float
    ) -> Optional[RuleViolation]:
        # 1取引のリスク上限（%）
        risk_amt = self._calc_risk_amount(entry, sl, lot)
        risk_pct = 100.0 * risk_amt / max(capital, 1e-9)
        if risk_pct > self.cfg["max_risk_per_trade_pct"]:
            return RuleViolation(
                code="MAX_RISK_EXCEEDED",
                message=f"1取引リスク {risk_pct:.2f}% が上限 {self.cfg['max_risk_per_trade_pct']}% を超過",
                details={
                    "risk_pct": risk_pct,
                    "risk_amt": risk_amt,
                    "capital": capital,
                },
                severity="ERROR",
            )
        return None

    def check_gambling_like(self, lot: float, recent_trades: List[Dict]) -> Optional[RuleViolation]:
        """
        ギャンブル的行為の簡易検出：
        - 短時間にロット急増
        - 連続エントリ間隔が極端に短い＋大ロット
        ※ 各プロジェクトのデータに合わせて閾値は適宜調整
        """
        if not recent_trades:
            return None
        # 過去N件の平均ロット比で急増（例：3倍超）
        last_avg = max(
            1e-9,
            sum(t.get("lot", 0) for t in recent_trades[-5:]) / min(5, len(recent_trades)),
        )
        if lot > 3.0 * last_avg and lot >= 0.5:  # 0.5ロット以上で急増
            return RuleViolation(
                code="GAMBLING_SPIKE",
                message=f"ロット急増検出 lot={lot} (recent_avg≈{last_avg:.2f})",
                details={"lot": lot, "recent_avg": last_avg},
                severity="WARN",
            )
        return None

    def check_one_day_single_symbol_profit_push(
        self, day_pnl_by_symbol: Dict[str, float], target_profit: float
    ) -> Optional[RuleViolation]:
        """
        同一銘柄・同日で目標利益を一気に狙う挙動のヒューリスティック。
        例：当日特定シンボルのPnLが目標の大部分を占める場合に警告。
        """
        if not day_pnl_by_symbol:
            return None
        top_sym = max(day_pnl_by_symbol, key=lambda k: day_pnl_by_symbol[k])
        top_val = day_pnl_by_symbol[top_sym]
        if target_profit > 0 and top_val >= 0.7 * target_profit:
            return RuleViolation(
                code="ONE_TRADE_PROFIT_PUSH",
                message=f"同日単一銘柄PnLが目標利益の大半を占有 ({top_sym}: {top_val:.0f} >= 70% of {target_profit:.0f})",
                details={
                    "symbol": top_sym,
                    "pnl": top_val,
                    "target_profit": target_profit,
                },
                severity="WARN",
            )
        return None

    def evaluate(
        self,
        *,
        symbol: str,
        side: str,
        entry_price: float,
        stop_loss_price: float,
        capital: float,
        lot: float,
        day_pnl_by_symbol: Optional[Dict[str, float]] = None,
        target_profit: Optional[float] = None,
        recent_trades: Optional[List[Dict]] = None,
    ) -> RuleResult:
        violations: List[RuleViolation] = []

        v = self.check_max_risk(capital, entry_price, stop_loss_price, lot)
        if v:
            violations.append(v)

        v = self.check_gambling_like(lot, recent_trades or [])
        if v:
            violations.append(v)

        if target_profit is not None and day_pnl_by_symbol is not None:
            v = self.check_one_day_single_symbol_profit_push(day_pnl_by_symbol, target_profit)
            if v:
                violations.append(v)

        # ERRORがなければ実行許可（WARNはログ&ダッシュボードで可視化）
        ok = all(v.severity != "ERROR" for v in violations)
        return RuleResult(ok=ok, violations=violations)
