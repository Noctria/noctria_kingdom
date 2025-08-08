#!/usr/bin/env python3
# coding: utf-8

"""
🛡️ Noctus Sentinella (feature_order準拠・標準特徴量dict対応)
- Plan層標準dict/feature_orderに完全準拠
- calculate_lot_and_risk: リスク・ロットサイズ判定（Fintokei等にも対応）
"""

import logging
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np

from src.core.risk_manager import RiskManager
from src.plan_data.standard_feature_schema import STANDARD_FEATURE_ORDER

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

class NoctusSentinella:
    def __init__(
        self,
        feature_order: Optional[List[str]] = None,
        col_map: Optional[Dict[str, str]] = None,
        risk_threshold: float = 0.02,
        max_spread: float = 0.018,
        min_liquidity: float = 120,
        max_volatility: float = 0.25
    ):
        self.feature_order = feature_order or STANDARD_FEATURE_ORDER
        # 標準特徴量名へのマッピング
        self.col_map = col_map or {
            "liquidity": "volume",
            "spread": "spread",
            "volatility": "volatility",
            "price": "price",
            "historical_data": "historical_data"
        }
        self.risk_threshold = risk_threshold
        self.max_spread = max_spread
        self.min_liquidity = min_liquidity
        self.max_volatility = max_volatility
        self.risk_manager: Optional[RiskManager] = None
        logging.info("NoctusSentinella（feature_order/標準dict準拠）着任。")

    def calculate_lot_and_risk(
        self,
        feature_dict: Dict[str, Any],
        side: str,
        entry_price: float,
        stop_loss_price: float,
        capital: float,
        risk_percent: float = 0.01,
        decision_id: Optional[str] = None,
        caller: Optional[str] = "king_noctria",
        reason: Optional[str] = None,
        min_risk: float = 0.005,
        max_risk: float = 0.01
    ) -> Dict[str, Any]:
        sl_distance = abs(entry_price - stop_loss_price)
        if sl_distance <= 0:
            return self._create_calc_result(
                decision="VETO",
                reason_text="ストップロスとエントリー価格が同一/逆方向です",
                lot=0, risk_amount=0, risk_percent=risk_percent,
                entry_price=entry_price, stop_loss_price=stop_loss_price,
                capital=capital, decision_id=decision_id, caller=caller, reason=reason
            )

        risk_amount = capital * risk_percent
        min_risk_amount = capital * min_risk
        max_risk_amount = capital * max_risk
        if not (min_risk_amount <= risk_amount <= max_risk_amount):
            return self._create_calc_result(
                decision="VETO",
                reason_text=f"リスク額 {risk_amount:.2f} が許容範囲（{min_risk_amount:.2f}～{max_risk_amount:.2f}）外",
                lot=0, risk_amount=risk_amount, risk_percent=risk_percent,
                entry_price=entry_price, stop_loss_price=stop_loss_price,
                capital=capital, decision_id=decision_id, caller=caller, reason=reason
            )
        lot = risk_amount / sl_distance
        lot = max(round(lot, 2), 0.01)

        # 標準dictから取得
        try:
            liquidity = feature_dict.get(self.col_map["liquidity"], None)
            spread = feature_dict.get(self.col_map["spread"], None)
            volatility = feature_dict.get(self.col_map["volatility"], None)
            price = feature_dict.get(self.col_map["price"], None)
            historical_data = feature_dict.get(self.col_map["historical_data"], None)
            if None in (liquidity, spread, volatility, price, historical_data) or getattr(historical_data, 'empty', True):
                raise ValueError("リスク評価に必要な特徴量が不足/不正。")
            self.risk_manager = RiskManager(historical_data=historical_data)
            risk_score = self.risk_manager.calculate_var_ratio(price)
        except Exception as e:
            return self._create_calc_result(
                decision="VETO",
                reason_text=f"特徴量不足/異常: {e}",
                lot=0, risk_amount=risk_amount, risk_percent=risk_percent,
                entry_price=entry_price, stop_loss_price=stop_loss_price,
                capital=capital, decision_id=decision_id, caller=caller, reason=reason
            )

        if liquidity < self.min_liquidity:
            return self._create_calc_result(
                decision="VETO",
                reason_text=f"流動性不足({liquidity}<{self.min_liquidity})",
                lot=0, risk_amount=risk_amount, risk_percent=risk_percent,
                entry_price=entry_price, stop_loss_price=stop_loss_price,
                capital=capital, decision_id=decision_id, caller=caller, reason=reason
            )
        if spread > self.max_spread:
            return self._create_calc_result(
                decision="VETO",
                reason_text=f"スプレッド過大({spread}>{self.max_spread})",
                lot=0, risk_amount=risk_amount, risk_percent=risk_percent,
                entry_price=entry_price, stop_loss_price=stop_loss_price,
                capital=capital, decision_id=decision_id, caller=caller, reason=reason
            )
        if volatility > self.max_volatility:
            return self._create_calc_result(
                decision="VETO",
                reason_text=f"ボラティリティ過大({volatility}>{self.max_volatility})",
                lot=0, risk_amount=risk_amount, risk_percent=risk_percent,
                entry_price=entry_price, stop_loss_price=stop_loss_price,
                capital=capital, decision_id=decision_id, caller=caller, reason=reason
            )
        if risk_score > self.risk_threshold:
            return self._create_calc_result(
                decision="VETO",
                reason_text=f"リスク過大({risk_score:.4f}>{self.risk_threshold:.4f})",
                lot=0, risk_amount=risk_amount, risk_percent=risk_percent,
                entry_price=entry_price, stop_loss_price=stop_loss_price,
                capital=capital, decision_id=decision_id, caller=caller, reason=reason
            )

        return self._create_calc_result(
            decision="APPROVE",
            reason_text="全監視項目正常/許可",
            lot=lot, risk_amount=risk_amount, risk_percent=risk_percent,
            entry_price=entry_price, stop_loss_price=stop_loss_price,
            capital=capital, decision_id=decision_id, caller=caller, reason=reason
        )

    def _create_calc_result(
        self,
        decision: str,
        reason_text: str,
        lot: float,
        risk_amount: float,
        risk_percent: float,
        entry_price: float,
        stop_loss_price: float,
        capital: float,
        decision_id: Optional[str],
        caller: Optional[str],
        reason: Optional[str]
    ) -> Dict[str, Any]:
        return {
            "name": "NoctusSentinella",
            "type": "risk_calc",
            "decision": decision,
            "reason": reason_text,
            "lot": round(lot, 3),
            "risk_amount": round(risk_amount, 2),
            "risk_percent": risk_percent,
            "entry_price": entry_price,
            "stop_loss": stop_loss_price,
            "capital": capital,
            "decision_id": decision_id,
            "caller": caller,
            "action_reason": reason
        }

# === テスト例 ===
if __name__ == "__main__":
    logging.info("--- Noctus: feature_order標準化テスト ---")
    dummy_hist_data = pd.DataFrame({'Close': np.random.normal(loc=150, scale=2, size=100)})
    dummy_hist_data['returns'] = dummy_hist_data['Close'].pct_change().dropna()
    feature_dict = {
        "price": 152.5,
        "volume": 150,
        "spread": 0.012,
        "volatility": 0.15,
        "historical_data": dummy_hist_data
    }
    noctus_ai = NoctusSentinella(feature_order=STANDARD_FEATURE_ORDER)
    res = noctus_ai.calculate_lot_and_risk(
        feature_dict=feature_dict,
        side="BUY",
        entry_price=152.60,
        stop_loss_price=152.30,
        capital=20000,
        risk_percent=0.007,
        decision_id="TEST-NOCTUS-1",
        caller="test",
        reason="unit_test"
    )
    print(f"🛡️ Noctusロット/リスク判定: {res['decision']} ({res['reason']}) Lot: {res['lot']}, Risk額: {res['risk_amount']}")
