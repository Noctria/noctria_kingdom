#!/usr/bin/env python3
# coding: utf-8

"""
🛡️ Noctus Sentinella (リスク＋ロット計算I/F付)
- calculate_lot_and_risk: Fintokei/一般口座のリスクに基づきロットサイズ判定＆注文判定
"""

import logging
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np

from src.core.risk_manager import RiskManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

class NoctusSentinella:
    def __init__(
        self,
        col_map: Optional[Dict[str, str]] = None,
        risk_threshold: float = 0.02,
        max_spread: float = 0.018,
        min_liquidity: float = 120,
        max_volatility: float = 0.25
    ):
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
        logging.info("リスク管理官ノクトゥス（特徴量dict同期型）着任。")

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
        """
        [NEW] 王やPlan層の公式リスク＆ロット計算API
        - ストップロス・エントリー距離とリスク許容割合からロット計算
        - Fintokei基準: リスク0.5%～1.0%のみ許可
        """
        sl_distance = abs(entry_price - stop_loss_price)
        if sl_distance <= 0:
            return self._create_calc_result(
                decision="VETO",
                reason_text="ストップロスとエントリー価格が同一/逆方向です",
                lot=0, risk_amount=0, risk_percent=risk_percent,
                entry_price=entry_price, stop_loss_price=stop_loss_price,
                capital=capital, decision_id=decision_id, caller=caller, reason=reason
            )

        # 許容リスク額
        risk_amount = capital * risk_percent
        # ガード: 0.5～1.0%以外NG
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
        # ロット計算: 1pip単位・最小ロット0.01想定
        lot = risk_amount / sl_distance
        lot = max(round(lot, 2), 0.01)

        # 他のPlan特徴量でリスク/流動性チェック
        try:
            liquidity = feature_dict.get(self.col_map["liquidity"], None)
            spread = feature_dict.get(self.col_map["spread"], None)
            volatility = feature_dict.get(self.col_map["volatility"], None)
            price = feature_dict.get(self.col_map["price"], None)
            historical_data = feature_dict.get(self.col_map["historical_data"], None)
            if None in (liquidity, spread, volatility, price, historical_data) or getattr(historical_data, 'empty', True):
                raise ValueError("リスク評価に必要な特徴量が不足または不正。")
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

    # 既存のassess()等は省略

# === テスト例 ===
if __name__ == "__main__":
    logging.info("--- Noctus: ロット/リスク計算テスト ---")
    dummy_hist_data = pd.DataFrame({'Close': np.random.normal(loc=150, scale=2, size=100)})
    dummy_hist_data['returns'] = dummy_hist_data['Close'].pct_change().dropna()
    feature_dict = {
        "price": 152.5,
        "volume": 150,
        "spread": 0.012,
        "volatility": 0.15,
        "historical_data": dummy_hist_data
    }
    noctus_ai = NoctusSentinella()
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
