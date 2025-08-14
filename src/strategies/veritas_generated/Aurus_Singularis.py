# src/strategies/veritas_generated/Aurus_Singularis.py
# -*- coding: utf-8 -*-
"""
Aurus_Singularis — Dummy but KPI-computable minimal strategy

- 外部依存なし（標準ライブラリのみ）
- propose(): 最低限の“シグナル”を返す
- backtest(): シグナル→ダミー売買→KPI算出まで一気通貫
- kpis(): 外部から trades を渡してKPIだけ算出も可
- ✅ GUI 連携用の公開APIを追加:
    * compute_kpis()         → dict を返す
    * run_backtest()         → (kpis, trades) を返す
    * class Strategy.compute_kpis() → 上記をラップ

使い方（単体実行テスト）:
    python -m strategies.veritas_generated.Aurus_Singularis
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Iterable, Tuple
from dataclasses import dataclass

NAME = "Aurus_Singularis"
VERSION = "0.2.0-dummy"


@dataclass
class Trade:
    ts: str          # ISO8601 string
    symbol: str
    side: str        # "BUY" | "SELL"
    qty: float
    entry: float
    exit: float
    ret_pct: float   # (exit/entry - 1) * 100


class AurusSingularis:
    """
    ダミー戦略
    - 入力データ（時系列の close 価格など）が無くても、決め打ちで擬似トレードを生成
    - KPI（win_rate, avg_return, max_drawdown, count）を返せる
    """

    def __init__(self, symbol: str = "USDJPY", lot: float = 1.0):
        self.symbol = symbol
        self.lot = lot

    # ---- 必須: 最低限の“提案/シグナル”IF（GUIなどが参照しても落ちない） ----
    def propose(self, market_data: Optional[Iterable[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        最小シグナル。市場データが無くても固定で返す。
        GUIやログで参照しても壊れないフィールド構成にしておく。
        """
        return [
            {"symbol": self.symbol, "action": "HOLD", "confidence": 0.0, "ts": "1970-01-01T00:00:00Z"}
        ]

    # ---- KPIを通すための最小バックテスト実装 ----
    def backtest(self, closes: Optional[List[float]] = None) -> Dict[str, Any]:
        """
        closes: ローソクの終値配列（任意）。無ければダミー価格列を自動生成。
        返り値: {"trades": List[TradeDict], "kpis": {...}}
        """
        if not closes or len(closes) < 6:
            # ダミーの価格列（単調増加+軽い揺らぎ）を生成
            closes = [100.0, 101.0, 100.5, 101.5, 102.0, 101.8, 102.4, 102.2, 102.9, 103.1]

        trades = self._make_dummy_trades_from_prices(closes)
        kpi = self.kpis(trades)
        return {
            "trades": [t.__dict__ for t in trades],
            "kpis": kpi,
        }

    # ---- KPI算出（外部から trades を渡されても使えるように独立関数化） ----
    @staticmethod
    def kpis(trades: List[Trade]) -> Dict[str, Any]:
        n = len(trades)
        if n == 0:
            return {
                "trades": 0,
                "win_rate": 0.0,            # %（0..100）
                "avg_return_pct": 0.0,      # %
                "pnl_sum_pct": 0.0,         # %
                "max_drawdown_pct": 0.0,    # %
            }
        wins = sum(1 for t in trades if t.ret_pct > 0)
        pnl_sum = sum(t.ret_pct for t in trades)
        avg_ret = pnl_sum / n
        # 簡易エクイティカーブ（％の加算で近似）
        curve = []
        acc = 0.0
        for t in trades:
            acc += t.ret_pct
            curve.append(acc)
        mdd = _max_drawdown_from_curve(curve)
        return {
            "trades": n,                                # 取引数
            "win_rate": round(100.0 * wins / n, 2),     # 勝率（%）
            "avg_return_pct": round(avg_ret, 4),        # 平均リターン（%）
            "pnl_sum_pct": round(pnl_sum, 4),           # 合計PnL（%）
            "max_drawdown_pct": round(mdd, 4),          # 最大DD（%）
        }

    # ---- 内部：価格列からダミー売買を合成 ----
    def _make_dummy_trades_from_prices(self, closes: List[float]) -> List[Trade]:
        """
        単純なパターン:
        - 偶数番目: BUY→次足でクローズ
        - 奇数番目: SELL→次足でクローズ
        """
        out: List[Trade] = []
        for i in range(len(closes) - 1):
            entry = closes[i]
            exit_ = closes[i + 1]
            if i % 2 == 0:  # BUY
                ret_pct = (exit_ / entry - 1.0) * 100.0
                side = "BUY"
            else:           # SELL
                ret_pct = (entry / exit_ - 1.0) * 100.0  # 価格下落でプラス
                side = "SELL"
            out.append(
                Trade(
                    ts=f"1970-01-01T00:00:{i:02d}Z",
                    symbol=self.symbol,
                    side=side,
                    qty=self.lot,
                    entry=round(entry, 5),
                    exit=round(exit_, 5),
                    ret_pct=round(ret_pct, 5),
                )
            )
        return out


# ---- ユーティリティ：最大ドローダウン（％カーブから） ----
def _max_drawdown_from_curve(curve_pct: List[float]) -> float:
    if not curve_pct:
        return 0.0
    peak = curve_pct[0]
    mdd = 0.0
    for x in curve_pct:
        if x > peak:
            peak = x
        dd = peak - x
        if dd > mdd:
            mdd = dd
    return mdd


# ============================================================
# ✅ GUI / ルーターから拾われる公開API（どれか1つあればOK）
# ============================================================
def compute_kpis() -> Dict[str, Any]:
    """
    GUI（/strategies/detail/<name> のフォールバック）が参照する最小API。
    戻り値は dict。 win_rate は 0..1 でも 0..100（%）でもOK。
    ここでは % で返す（上位は自動で扱える）。
    """
    strat = AurusSingularis()
    bt = strat.backtest()
    return dict(bt["kpis"])


def run_backtest() -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    互換API: (kpis, trades) のタプルを返す。
    """
    strat = AurusSingularis()
    bt = strat.backtest()
    kpis = dict(bt["kpis"])
    trades = list(bt["trades"])
    return kpis, trades


class Strategy:
    """
    互換用クラスAPI（存在すれば GUI 側が拾える）
    """
    def compute_kpis(self) -> Dict[str, Any]:
        return compute_kpis()


# ---- 単体テスト実行（python -m で動作確認可能） ----
if __name__ == "__main__":
    strat = AurusSingularis()
    bt = strat.backtest()  # ダミー価格列で実行
    print(f"[{NAME}] KPIs:", bt["kpis"])
    print(f"[{NAME}] Trades sample:", bt["trades"][:3])


__all__ = [
    "NAME", "VERSION",
    "Trade", "AurusSingularis",
    "compute_kpis", "run_backtest", "Strategy",
]
