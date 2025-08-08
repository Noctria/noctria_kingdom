#!/usr/bin/env python3
# coding: utf-8

"""
⚡ Levia Tempest (標準feature_order準拠)
- Plan層の標準特徴量（feature_dict, feature_order）で即時判定
"""

import logging
from typing import Dict, Any, Optional, List
from src.plan_data.standard_feature_schema import STANDARD_FEATURE_ORDER

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

class LeviaTempest:
    def __init__(
        self,
        feature_order: Optional[List[str]] = None,
        price_col: str = "USDJPY_Close",
        prev_price_col: str = "USDJPY_Close",
        volume_col: str = "USDJPY_Volume_MA5",
        spread_col: str = "USDJPY_Volatility_5d",
        volatility_col: str = "USDJPY_Volatility_5d",
        price_threshold: float = 0.0005,
        min_liquidity: float = 120,
        max_spread: float = 0.018,
        max_volatility: float = 0.2
    ):
        self.feature_order = feature_order or STANDARD_FEATURE_ORDER
        self.price_col = price_col
        self.prev_price_col = prev_price_col
        self.volume_col = volume_col
        self.spread_col = spread_col
        self.volatility_col = volatility_col
        self.price_threshold = price_threshold
        self.min_liquidity = min_liquidity
        self.max_spread = max_spread
        self.max_volatility = max_volatility
        logging.info("LeviaTempest(標準feature_order準拠) 準備OK")

    def _calculate_price_change(self, feature_dict: Dict[str, Any]) -> float:
        price = feature_dict.get(self.price_col, 0.0)
        prev_price = feature_dict.get(self.prev_price_col, price)
        return price - prev_price

    def propose(
        self,
        feature_dict: Dict[str, Any],
        decision_id: Optional[str] = None,
        caller: Optional[str] = "king_noctria",
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        liquidity = feature_dict.get(self.volume_col, 0.0)
        spread = feature_dict.get(self.spread_col, 0.0)
        volatility = feature_dict.get(self.volatility_col, 0.0)
        price_change = self._calculate_price_change(feature_dict)

        if liquidity < self.min_liquidity:
            logging.warning(f"流動性低下: {liquidity} < {self.min_liquidity}。HOLD")
            return self._create_proposal("HOLD", 0.0, feature_dict, decision_id, caller, reason)
        if spread > self.max_spread:
            logging.warning(f"スプレッド過大: {spread} > {self.max_spread}。HOLD")
            return self._create_proposal("HOLD", 0.0, feature_dict, decision_id, caller, reason)
        if volatility > self.max_volatility:
            logging.warning(f"ボラ過大: {volatility} > {self.max_volatility}。HOLD")
            return self._create_proposal("HOLD", 0.0, feature_dict, decision_id, caller, reason)

        score = min(abs(price_change) / (self.price_threshold + 1e-9), 1.0)
        if price_change > self.price_threshold:
            signal = "BUY"
        elif price_change < -self.price_threshold:
            signal = "SELL"
        else:
            signal = "HOLD"
            score = 0.0

        return self._create_proposal(signal, score, feature_dict, decision_id, caller, reason)

    def _create_proposal(
        self,
        signal: str,
        score: float,
        feature_dict: Dict[str, Any],
        decision_id: Optional[str],
        caller: Optional[str],
        reason: Optional[str]
    ) -> Dict[str, Any]:
        return {
            "name": "LeviaTempest",
            "type": "scalping_signal",
            "signal": signal,
            "confidence": round(score, 4),
            "symbol": feature_dict.get("symbol", "USDJPY"),
            "priority": "very_high",
            "decision_id": decision_id,
            "caller": caller,
            "reason": reason
        }
