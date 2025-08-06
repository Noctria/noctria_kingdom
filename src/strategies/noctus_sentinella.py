#!/usr/bin/env python3
# coding: utf-8

"""
🛡️ Noctus Sentinella (Plan特徴量同期対応)
- 全リスク評価に decision_id/caller/理由/feature_dict
- Plan層（feature_engineer/collector）で生成した任意の特徴量セット対応
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
        """
        col_map: Plan層の特徴量名とNoctus側パラメータのマッピング
          例: {"liquidity": "USDJPY_Volume", "spread": "USDJPY_Spread", ...}
        """
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
        # HOLDは常に承認
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

# === テスト例 ===
if __name__ == "__main__":
    logging.info("--- Noctus: Plan特徴量dictテスト ---")
    # Plan層の特徴量dict例
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
    res = noctus_ai.assess(feature_dict, "BUY", decision_id="TEST-NOCTUS-1", caller="__main__", reason="Plan特徴量dictテスト")
    print(f"🛡️ ノクトゥス判定: {res['decision']} ({res['reason']})")
