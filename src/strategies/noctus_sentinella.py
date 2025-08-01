#!/usr/bin/env python3
# coding: utf-8

"""
🛡️ Noctus Sentinella (理想形 v2.2 - decision_id伝播対応)
- 全リスク評価に decision_id/caller/理由 を一元化
- 必ず王（Noctria）経由で呼ばれる前提
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from src.core.risk_manager import RiskManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

class NoctusSentinella:
    def __init__(self, risk_threshold: float = 0.02, max_spread: float = 0.018, min_liquidity: float = 120, max_volatility: float = 0.25):
        self.risk_threshold = risk_threshold
        self.max_spread = max_spread
        self.min_liquidity = min_liquidity
        self.max_volatility = max_volatility
        self.risk_manager: Optional[RiskManager] = None
        logging.info("リスク管理官ノクトゥス、着任。王国の影を見守ります。")

    def assess(
        self,
        market_data: Dict[str, Any],
        proposed_action: str,
        decision_id: Optional[str] = None,
        caller: Optional[str] = "king_noctria",
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        必ずdecision_id/caller/理由付きでリスク評価返却
        """
        logging.info(f"進言『{proposed_action}』に対するリスク評価を開始します。")
        # HOLDは常に承認
        if proposed_action == "HOLD":
            logging.info("行動『HOLD』は承認されました。影は動くべき時ではない。")
            return self._create_assessment("APPROVE", "No action proposed.", 0.0, decision_id, caller, reason)

        try:
            liquidity = market_data.get("volume", None)
            spread = market_data.get("spread", None)
            volatility = market_data.get("volatility", None)
            price = market_data.get("price", None)
            historical_data = market_data.get("historical_data", None)
            if None in (liquidity, spread, volatility, price, historical_data) or getattr(historical_data, 'empty', True):
                raise ValueError("リスク評価に必要な市場データまたはヒストリカルデータが欠損しています。")
            self.risk_manager = RiskManager(historical_data=historical_data)
            risk_score = self.risk_manager.calculate_var_ratio(price)
        except Exception as e:
            logging.error(f"評価不能。安全のため拒否。詳細: {e}")
            return self._create_assessment("VETO", f"Missing or invalid market data: {e}", 1.0, decision_id, caller, reason)

        if liquidity < self.min_liquidity:
            return self._create_assessment(
                "VETO",
                f"市場の活気が失われています（流動性: {liquidity} < 閾値: {self.min_liquidity}）。",
                risk_score, decision_id, caller, reason
            )
        if spread > self.max_spread:
            return self._create_assessment(
                "VETO",
                f"市場の霧が深すぎます（スプレッド: {spread} > 閾値: {self.max_spread}）。",
                risk_score, decision_id, caller, reason
            )
        if volatility > self.max_volatility:
            return self._create_assessment(
                "VETO",
                f"市場が荒れ狂っています（ボラティリティ: {volatility} > 閾値: {self.max_volatility}）。",
                risk_score, decision_id, caller, reason
            )
        if risk_score > self.risk_threshold:
            return self._create_assessment(
                "VETO",
                f"予測される損失が許容範囲を超えています（リスクスコア: {risk_score:.4f} > 閾値: {self.risk_threshold:.4f}）。",
                risk_score, decision_id, caller, reason
            )

        return self._create_assessment(
            "APPROVE",
            "全ての監視項目は正常範囲内。影からの警告はありません。",
            risk_score, decision_id, caller, reason
        )

    def _create_assessment(
        self,
        decision: str,
        reason_text: str,
        score: float,
        decision_id: Optional[str],
        caller: Optional[str],
        reason: Optional[str]
    ) -> Dict[str, Any]:
        if decision == "VETO":
            logging.warning(f"【拒否権発動】理由: {reason_text}")
        else:
            logging.info(f"【承認】理由: {reason_text}")
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

# ========================================
# ✅ 単体テスト＆実行ブロック
# ========================================
if __name__ == "__main__":
    logging.info("--- リスク管理官ノクトゥス、単独試練の儀を開始 ---")
    noctus_ai = NoctusSentinella()
    dummy_hist_data = pd.DataFrame({'Close': np.random.normal(loc=150, scale=2, size=100)})
    dummy_hist_data['returns'] = dummy_hist_data['Close'].pct_change().dropna()
    safe_market_data = {
        "price": 152.5, "volume": 150, "spread": 0.012,
        "volatility": 0.15, "historical_data": dummy_hist_data
    }
    # 各評価にdecision_id, caller, reasonを明示
    safe_assessment = noctus_ai.assess(safe_market_data, "BUY", decision_id="KC-EX-1", caller="king_noctria", reason="シナリオ1")
    print(f"🛡️ ノクトゥスの最終判断: {safe_assessment['decision']} (理由: {safe_assessment['reason']})")

    logging.info("--- リスク管理官ノクトゥス、単独試練の儀を完了 ---")
