#!/usr/bin/env python3
# coding: utf-8

"""
⚡ Levia Tempest (v3.0 - Plan特徴量拡張対応)
- 高速反応型スキャルピングAI
- Plan層の任意の特徴量（feature_dict/feature_order）でロジックを柔軟化
- 必ずNoctria王経由でのみ呼ばれることを前提
"""

import logging
from typing import Dict, Any, Optional, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

class LeviaTempest:
    """
    瞬きの間に好機を見出すスキャルピングAI。
    """

    def __init__(
        self,
        feature_order: Optional[List[str]] = None,
        price_col: str = "price",
        prev_price_col: str = "previous_price",
        volume_col: str = "volume",
        spread_col: str = "spread",
        volatility_col: str = "volatility",
        price_threshold: float = 0.0005,
        min_liquidity: float = 120,
        max_spread: float = 0.018,
        max_volatility: float = 0.2
    ):
        self.feature_order = feature_order  # Plan層で渡すことを推奨
        self.price_col = price_col
        self.prev_price_col = prev_price_col
        self.volume_col = volume_col
        self.spread_col = spread_col
        self.volatility_col = volatility_col
        self.price_threshold = price_threshold
        self.min_liquidity = min_liquidity
        self.max_spread = max_spread
        self.max_volatility = max_volatility
        logging.info("スキャルピングAIレビアv3、準備万端。特徴量自動対応。")

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
        """
        Plan層から任意の特徴量dict（feature_order順）をそのまま受け取って意思決定
        """
        logging.info("Levia: 特徴量dictからスキャルピング条件を判定します。")

        # 必要な特徴量がなければデフォルト値で進む
        liquidity = feature_dict.get(self.volume_col, 0.0)
        spread = feature_dict.get(self.spread_col, 0.0)
        volatility = feature_dict.get(self.volatility_col, 0.0)
        price_change = self._calculate_price_change(feature_dict)

        # 柔軟性重視で閾値を特徴量側で上書きできる設計も可
        price_threshold = feature_dict.get("levia_price_threshold", self.price_threshold)
        min_liquidity = feature_dict.get("levia_min_liquidity", self.min_liquidity)
        max_spread = feature_dict.get("levia_max_spread", self.max_spread)
        max_volatility = feature_dict.get("levia_max_volatility", self.max_volatility)

        if liquidity < min_liquidity:
            logging.warning(f"流動性低下: {liquidity} < {min_liquidity}。HOLDします。")
            return self._create_proposal("HOLD", 0.0, feature_dict, decision_id, caller, reason)

        if spread > max_spread:
            logging.warning(f"スプレッド過大: {spread} > {max_spread}。HOLDします。")
            return self._create_proposal("HOLD", 0.0, feature_dict, decision_id, caller, reason)

        if volatility > max_volatility:
            logging.warning(f"ボラ過大: {volatility} > {max_volatility}。HOLDします。")
            return self._create_proposal("HOLD", 0.0, feature_dict, decision_id, caller, reason)

        score = min(abs(price_change) / (price_threshold + 1e-9), 1.0)
        if price_change > price_threshold:
            signal = "BUY"
            logging.info(f"上昇検知: {signal} (score={score:.2f})")
        elif price_change < -price_threshold:
            signal = "SELL"
            logging.info(f"下降検知: {signal} (score={score:.2f})")
        else:
            signal = "HOLD"
            score = 0.0
            logging.info("好機無し: HOLD。")

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
        """decision_id/caller/理由は全て返却"""
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

# ========================================
# ✅ テスト例
# ========================================
if __name__ == "__main__":
    logging.info("--- Levia v3: Plan特徴量dictテスト ---")
    # Plan層で生成した特徴量セット（任意拡張OK）
    test_feat = {
        "price": 1.2050,
        "previous_price": 1.2044,
        "volume": 150,
        "spread": 0.012,
        "volatility": 0.15,
        "symbol": "USDJPY"
    }
    levia_ai = LeviaTempest()
    proposal = levia_ai.propose(test_feat, decision_id="TEST-LEVIA-1", caller="__main__", reason="Plan層dictテスト")
    print("⚡ レヴィアの進言:", proposal)
