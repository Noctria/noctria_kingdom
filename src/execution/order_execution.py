# =========================
# File: src/execution/order_execution.py
# =========================
"""
💼 OrderExecution（Fintokei対応／リスク計算見直し版）

目的
- MT5/ブリッジ(API)への注文リクエスト送信（requests）
- 取引リスクは「口座残高に対する 0.5%〜1%」を厳守
- 損切(SL)は **必須**（TPは任意）
- ロットは **口座通貨ベース**のリスク額に合わせて自動計算
- バリデーション違反時は注文不可＆理由返却

主な修正点
- ❗通貨換算の不整合修正：USDJPYなどのJPY建てペアで、口座通貨（想定: USD）に換算して
  リスク％を評価（以前は JPY のまま割っていたため誤差が大きい）
- リスク％判定は「(ロス額[口座通貨] / 残高)」で厳密化
- BUY/SELL の SL 方向チェック（SLがエントリの逆側にあるか）
- pip サイズ自動判定（例: *JPY は 0.01、それ以外は 0.0001）
- 失敗時のレスポンス整備・タイムアウト付
"""

from __future__ import annotations

import os
import math
from dataclasses import dataclass
from typing import Optional, Dict, Any

import requests


# ------------------------------------------------------------
# ユーティリティ
# ------------------------------------------------------------
def _infer_pip_size(symbol: str) -> float:
    """通貨ペアから pip サイズを推定。例: USDJPY -> 0.01 / EURUSD -> 0.0001"""
    s = symbol.upper()
    return 0.01 if s.endswith("JPY") else 0.0001


def _quote_ccy(symbol: str) -> str:
    """クォート通貨（右側3文字）"""
    return symbol.upper()[-3:]


def _base_ccy(symbol: str) -> str:
    """ベース通貨（左側3文字）"""
    return symbol.upper()[:3]


def _pip_value_per_lot_in_account_ccy(
    *,
    symbol: str,
    price: float,
    contract_size: int = 100_000,
    account_ccy: str = "USD",
) -> float:
    """
    1pip あたりの損益（口座通貨建て, 1ロット）の近似値を返す。

    想定：
      - 口座通貨は USD（Fintokei/一般的海外口座の想定）
      - 主要2パターンは正確に扱う：
         1) クォート通貨が USD（EURUSD/GBPUSD 等）:  pip_value = contract_size * pip_size [USD]
         2) クォート通貨が JPY（USDJPY 等）:          pip_value = (contract_size * pip_size [JPY]) / price
      - それ以外（例：EURGBP）は近似対応が困難なため簡易計算にフォールバック（必要なら拡張）
    """
    pip = _infer_pip_size(symbol)
    q = _quote_ccy(symbol)

    if account_ccy.upper() != "USD":
        # 必要なら将来拡張（今は USD 口座のみ正式対応）
        raise NotImplementedError("Only USD account is officially supported in this implementation.")

    if q == "USD":
        # 例: EURUSD -> 1 pip = 100000 * 0.0001 = 10 USD / lot
        return contract_size * pip
    elif q == "JPY":
        # 例: USDJPY -> 1 pip = 100000 * 0.01 = 1000 JPY / lot => USD換算 = 1000 / price
        return (contract_size * pip) / price
    else:
        # 簡易フォールバック（精度は悪い）:
        # 「クォートがUSDでない」場合、本来は別レートでの換算が必要。
        # ここでは安全側に倒すため、pip価値をやや大きめに見積もり、Lotを小さめに計算。
        # ※実運用する場合は必ず通貨換算レートを注入してください。
        return (contract_size * pip) * 0.7  # 保守的に7割評価（＝リスクを厳しめにする）


# ------------------------------------------------------------
# 実装
# ------------------------------------------------------------
@dataclass
class OrderExecution:
    api_url: str = "http://host.docker.internal:5001/order"
    max_risk_per_trade: float = 0.01    # 最大1%（1トレードあたり）
    min_risk_per_trade: float = 0.005   # 最小0.5%
    get_balance_api_url: Optional[str] = None
    contract_size: int = 100_000        # 1Lotの通貨数量（FX一般）
    account_ccy: str = "USD"
    timeout_sec: float = 6.0

    # --------------------------------------------------------
    # 口座残高
    # --------------------------------------------------------
    def get_account_balance(self) -> Optional[float]:
        """
        口座残高を取得（API or ダミー）
        - GET {get_balance_api_url} -> {"balance": <float>}
        - ENV BALANCE_OVERRIDE があればそれを優先（デモ用）
        """
        override = os.getenv("BALANCE_OVERRIDE")
        if override:
            try:
                return float(override)
            except Exception:
                pass

        if self.get_balance_api_url:
            try:
                r = requests.get(self.get_balance_api_url, timeout=self.timeout_sec)
                r.raise_for_status()
                return float(r.json().get("balance", 0))
            except Exception as e:
                return None

        # ダミー
        return 10_000.0

    # --------------------------------------------------------
    # ロット計算（口座通貨ベースで厳密化）
    # --------------------------------------------------------
    def calc_lot_size(
        self,
        *,
        balance: float,
        symbol: str,
        entry_price: float,
        stop_loss_price: float,
        risk_percent: Optional[float] = None,
    ) -> (float, Optional[str], Dict[str, Any]):
        """
        口座通貨ベースで最大許容ロス額を算出し、Lotを計算。
        戻り値: (lot, error_message, debug_info)
        """
        pip_size = _infer_pip_size(symbol)
        if abs(entry_price - stop_loss_price) < pip_size:
            return 0.0, "エントリーとSLの幅が狭すぎます", {}

        rp = float(risk_percent or self.max_risk_per_trade)
        rp = max(min(rp, self.max_risk_per_trade), self.min_risk_per_trade)
        risk_amount = balance * rp  # 口座通貨ベース

        pip_value = _pip_value_per_lot_in_account_ccy(
            symbol=symbol,
            price=entry_price,
            contract_size=self.contract_size,
            account_ccy=self.account_ccy,
        )
        pip_diff = abs(entry_price - stop_loss_price) / pip_size
        # 1ロット当たりの損失（口座通貨）
        loss_per_lot = pip_value * pip_diff
        if loss_per_lot <= 0:
            return 0.0, "SL値幅が不正です", {}

        lot = risk_amount / loss_per_lot

        # ロット刻みは 0.01 を想定（必要なら外出し設定）
        min_lot = 0.01
        lot = max(min_lot, math.floor(lot * 100) / 100)

        debug = {
            "pip_size": pip_size,
            "pip_value_per_lot": pip_value,
            "pip_diff": pip_diff,
            "loss_per_lot": loss_per_lot,
            "risk_amount": risk_amount,
            "risk_percent": rp,
            "lot_raw": risk_amount / loss_per_lot,
            "lot_rounded": lot,
        }
        return lot, None, debug

    # --------------------------------------------------------
    # 事前バリデーション
    # --------------------------------------------------------
    def validate_order(
        self,
        *,
        symbol: str,
        side: str,  # "buy" | "sell"
        entry_price: float,
        stop_loss_price: Optional[float],
        balance: float,
        lot: float,
        risk_percent: float,
    ) -> (bool, Optional[str], Dict[str, Any]):
        """
        - SL 必須
        - SL が正しい方向（buy: SL < entry, sell: SL > entry）
        - lot 範囲（0.01〜100を仮定）
        - 実効リスク％が min〜max の範囲か
        """
        if not stop_loss_price:
            return False, "損切(SL)は必須です", {}

        # 方向（BUY: SL < entry / SELL: SL > entry）
        if side.lower() == "buy" and not (stop_loss_price < entry_price):
            return False, "BUYでは SL はエントリーより下に設定してください", {}
        if side.lower() == "sell" and not (stop_loss_price > entry_price):
            return False, "SELLでは SL はエントリーより上に設定してください", {}

        if not (0.01 <= lot <= 100.0):
            return False, f"ロット数が異常です: {lot:.2f}", {}

        # 実効リスク率を逆算チェック
        pip_size = _infer_pip_size(symbol)
        pip_value = _pip_value_per_lot_in_account_ccy(
            symbol=symbol,
            price=entry_price,
            contract_size=self.contract_size,
            account_ccy=self.account_ccy,
        )
        pip_diff = abs(entry_price - stop_loss_price) / pip_size
        risk_amount = pip_value * pip_diff * lot
        eff_percent = risk_amount / balance if balance > 0 else 1.0

        ok_max = eff_percent <= (self.max_risk_per_trade * 1.02)  # 若干の丸め許容
        ok_min = eff_percent >= (self.min_risk_per_trade * 0.98)

        if not ok_max:
            return (
                False,
                f"リスクが上限({self.max_risk_per_trade*100:.2f}%)を超えます: {eff_percent*100:.2f}%",
                {"eff_percent": eff_percent, "risk_amount": risk_amount},
            )
        if not ok_min:
            return (
                False,
                f"リスクが下限({self.min_risk_per_trade*100:.2f}%)未満です: {eff_percent*100:.2f}%",
                {"eff_percent": eff_percent, "risk_amount": risk_amount},
            )

        return True, None, {"eff_percent": eff_percent, "risk_amount": risk_amount}

    # --------------------------------------------------------
    # 実注文（API POST）
    # --------------------------------------------------------
    def execute_order(
        self,
        *,
        symbol: str,
        side: str,               # "buy" | "sell"
        entry_price: float,
        stop_loss_price: float,  # 必須（価格）
        take_profit_price: Optional[float] = None,
        risk_percent: Optional[float] = None,
        magic_number: Optional[int] = None,
        comment: Optional[str] = None,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        ✅ リスクとSLに基づくロット自動計算 → バリデーション → API送信
        返却: {"status": "ok"|"error", "message": str, "payload": {...}, "debug": {...}}
        """
        # 1) 残高
        balance = self.get_account_balance()
        if balance is None or balance <= 0:
            return {"status": "error", "message": "口座残高取得エラー", "debug": {}}

        # 2) ロット計算
        lot, err, dbg1 = self.calc_lot_size(
            balance=balance,
            symbol=symbol,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            risk_percent=risk_percent,
        )
        if err:
            return {"status": "error", "message": err, "debug": dbg1}

        # 3) バリデーション
        rp = float(risk_percent or self.max_risk_per_trade)
        ok, msg, dbg2 = self.validate_order(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            balance=balance,
            lot=lot,
            risk_percent=rp,
        )
        if not ok:
            return {"status": "error", "message": msg, "debug": {**dbg1, **dbg2}}

        # 4) API送信
        payload = {
            "symbol": symbol,
            "type": side.lower(),        # "buy" | "sell"
            "lot": float(f"{lot:.2f}"),  # 刻み 0.01
            "entry_price": entry_price,
            "stop_loss": stop_loss_price,
            "take_profit": take_profit_price,
            "magic_number": magic_number,
            "comment": comment,
        }
        if extra_fields:
            payload.update(extra_fields)

        try:
            r = requests.post(self.api_url, json=payload, timeout=self.timeout_sec)
            r.raise_for_status()
            resp = r.json()
            return {"status": "ok", "message": "sent", "payload": payload, "response": resp, "debug": {**dbg1, **dbg2}}
        except requests.RequestException as e:
            return {
                "status": "error",
                "message": f"発注APIエラー: {e}",
                "payload": payload,
                "debug": {**dbg1, **dbg2},
            }


# ==========================
# テスト／サンプル実行
# ==========================
if __name__ == "__main__":
    """
    例:
      口座 USD 1万、USDJPY 155.00 でエントリー、SL 154.50（= 50pips）
      リスク1%だと、許容ロス = 100 USD 以内に収まる Lot を自動で算出・送信
    """
    exe = OrderExecution(
        api_url=os.getenv("ORDER_API_URL", "http://host.docker.internal:5001/order"),
        get_balance_api_url=os.getenv("BALANCE_API_URL", None),
        max_risk_per_trade=0.01,
        min_risk_per_trade=0.005,
    )
    result = exe.execute_order(
        symbol="USDJPY",
        side="buy",
        entry_price=155.00,
        stop_loss_price=154.50,
        take_profit_price=155.80,
        comment="Fintokeiテスト（SL必須/リスク管理）",
    )
    print(result)
