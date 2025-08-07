#!/usr/bin/env python3
# coding: utf-8

"""
🛡️ Noctus Sentinella (Plan特徴量同期対応)
- ロット計算＆リスク許容チェックI/F新設
"""

import logging
from typing import Dict, Any, Optional
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

    def assess(
        self,
        feature_dict: Dict[str, Any],
        proposed_action: str,
        decision_id: Optional[str] = None,
        caller: Optional[str] = "king_noctria",
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        logging.info(f"進言『{proposed_action}』に対するリスク評価を開始。特徴量dict受領。")
        if proposed_action == "HOLD":
            return self._create_assessment("APPROVE", "No action proposed.", 0.0, decision_id, caller, reason)
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
            logging.error(f"評価不能: {e}")
            return self._create_assessment("VETO", f"特徴量不足/異常: {e}", 1.0, decision_id, caller, reason)
        if liquidity < self.min_liquidity:
            return self._create_assessment("VETO", f"流動性不足({liquidity}<{self.min_liquidity})", risk_score, decision_id, caller, reason)
        if spread > self.max_spread:
            return self._create_assessment("VETO", f"スプレッド過大({spread}>{self.max_spread})", risk_score, decision_id, caller, reason)
        if volatility > self.max_volatility:
            return self._create_assessment("VETO", f"ボラティリティ過大({volatility}>{self.max_volatility})", risk_score, decision_id, caller, reason)
        if risk_score > self.risk_threshold:
            return self._create_assessment("VETO", f"リスク過大({risk_score:.4f}>{self.risk_threshold:.4f})", risk_score, decision_id, caller, reason)
        return self._create_assessment("APPROVE", "全監視項目正常", risk_score, decision_id, caller, reason)

    def _create_assessment(
        self,
        decision: str,
        reason_text: str,
        score: float,
        decision_id: Optional[str],
        caller: Optional[str],
        reason: Optional[str]
    ) -> Dict[str, Any]:
        return {
            "name": "NoctusSentinella",
            "type": "risk_assessment",
            "decision": decision,
            "risk_score": round(score, 4),
            "reason": reason_text,
            "decision_id": decision_id,
            "caller": caller,
            "action_reason": reason
        }

    # 新設: ロット/リスク判定I/F
    def calculate_lot_and_risk(
        self,
        symbol: str,
        entry_price: float,
        stop_loss_price: float,
        capital: float,
        risk_percent_min: float = 0.005,
        risk_percent_max: float = 0.01,
        pip_value: Optional[float] = None
    ) -> dict:
        """
        指定条件下で「許容リスク範囲0.5%～1%」をガードしつつロットサイズ計算＆エラー理由返却
        pip_value: 1ロットあたり1pipsの金額（未指定ならUSDJPY→1000円仮実装）

        Returns:
            dict: { "ok": bool, "lot": float, "risk_amount": float, "msg": str }
        """
        if pip_value is None:
            pip_value = 1000.0  # USDJPY用仮値

        sl_pips = abs(entry_price - stop_loss_price) / 0.01
        if sl_pips <= 0:
            return {"ok": False, "lot": 0, "risk_amount": 0, "msg": "SLがエントリー価格と同一/逆方向"}

        for rp in [risk_percent_max, risk_percent_min]:
            if rp < 0 or rp > 1:
                return {"ok": False, "lot": 0, "risk_amount": 0, "msg": "リスク率異常"}

        risk_amount = capital * risk_percent_max
        min_risk = capital * risk_percent_min
        max_risk = capital * risk_percent_max

        risk_per_lot = sl_pips * pip_value
        if risk_per_lot <= 0:
            return {"ok": False, "lot": 0, "risk_amount": 0, "msg": "SL幅またはpip値異常"}

        lot = risk_amount / risk_per_lot

        if not (min_risk <= lot * risk_per_lot <= max_risk):
            return {
                "ok": False,
                "lot": lot,
                "risk_amount": lot * risk_per_lot,
                "msg": f"許容リスク範囲外: {min_risk:.2f}～{max_risk:.2f}円, この注文: {lot * risk_per_lot:.2f}円"
            }

        return {
            "ok": True,
            "lot": lot,
            "risk_amount": lot * risk_per_lot,
            "msg": "許容範囲内でロット決定"
        }
