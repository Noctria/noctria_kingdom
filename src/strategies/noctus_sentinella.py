#!/usr/bin/env python3
# coding: utf-8

"""
🛡️ Noctus Sentinella (v2.1)
- Noctria Kingdomの守護者。センチメントを監視し、システム全体のリスクを管理する。
- VaR、流動性、ボラティリティなど複数の観点から提案されたアクションのリスクを評価。
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from src.core.risk_manager import RiskManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

class NoctusSentinella:
    """
    王国の影として市場のセンチメントを監視し、あらゆるリスクを検知する守護者AI。
    """

    def __init__(self, risk_threshold: float = 0.02, max_spread: float = 0.018, min_liquidity: float = 120, max_volatility: float = 0.25):
        self.risk_threshold = risk_threshold
        self.max_spread = max_spread
        self.min_liquidity = min_liquidity
        self.max_volatility = max_volatility
        self.risk_manager: Optional[RiskManager] = None
        logging.info("リスク管理官ノクトゥス、着任。王国の影を見守ります。")

    def assess(self, market_data: Dict[str, Any], proposed_action: str) -> Dict[str, Any]:
        """
        市場データと提案されたアクションに基づき、リスクを評価し最終判断を下す。
        'APPROVE' (承認) または 'VETO' (拒否)
        """
        logging.info(f"進言『{proposed_action}』に対するリスク評価を開始します。")

        # HOLDは常に承認
        if proposed_action == "HOLD":
            logging.info("行動『HOLD』は承認されました。影は動くべき時ではない。")
            return self._create_assessment("APPROVE", "No action proposed.", 0.0)

        try:
            liquidity = market_data.get("volume", None)
            spread = market_data.get("spread", None)
            volatility = market_data.get("volatility", None)
            price = market_data.get("price", None)
            historical_data = market_data.get("historical_data", None)

            # 入力の妥当性
            if None in (liquidity, spread, volatility, price, historical_data) or getattr(historical_data, 'empty', True):
                raise ValueError("リスク評価に必要な市場データまたはヒストリカルデータが欠損しています。")

            self.risk_manager = RiskManager(historical_data=historical_data)
            risk_score = self.risk_manager.calculate_var_ratio(price)

        except Exception as e:
            logging.error(f"評価不能。安全のため拒否。詳細: {e}")
            return self._create_assessment("VETO", f"Missing or invalid market data: {e}", 1.0)

        # --- 各種リスク評価 ---
        if liquidity < self.min_liquidity:
            return self._create_assessment(
                "VETO",
                f"市場の活気が失われています（流動性: {liquidity} < 閾値: {self.min_liquidity}）。",
                risk_score
            )
        if spread > self.max_spread:
            return self._create_assessment(
                "VETO",
                f"市場の霧が深すぎます（スプレッド: {spread} > 閾値: {self.max_spread}）。",
                risk_score
            )
        if volatility > self.max_volatility:
            return self._create_assessment(
                "VETO",
                f"市場が荒れ狂っています（ボラティリティ: {volatility} > 閾値: {self.max_volatility}）。",
                risk_score
            )
        if risk_score > self.risk_threshold:
            return self._create_assessment(
                "VETO",
                f"予測される損失が許容範囲を超えています（リスクスコア: {risk_score:.4f} > 閾値: {self.risk_threshold:.4f}）。",
                risk_score
            )

        # 全てのリスク評価を通過
        return self._create_assessment(
            "APPROVE",
            "全ての監視項目は正常範囲内。影からの警告はありません。",
            risk_score
        )

    def _create_assessment(self, decision: str, reason: str, score: float) -> Dict[str, Any]:
        """評価結果を整形して返すヘルパー関数"""
        if decision == "VETO":
            logging.warning(f"【拒否権発動】理由: {reason}")
        else:
            logging.info(f"【承認】理由: {reason}")

        return {
            "name": "NoctusSentinella",
            "type": "risk_assessment",
            "decision": decision,
            "risk_score": round(score, 4),
            "reason": reason
        }

# ========================================
# ✅ 単体テスト＆実行ブロック
# ========================================
if __name__ == "__main__":
    logging.info("--- リスク管理官ノクトゥス、単独試練の儀を開始 ---")
    noctus_ai = NoctusSentinella()

    # テスト用のダミーヒストリカルデータを作成
    dummy_hist_data = pd.DataFrame({
        'Close': np.random.normal(loc=150, scale=2, size=100)
    })
    dummy_hist_data['returns'] = dummy_hist_data['Close'].pct_change().dropna()

    # --- シナリオ1: 安全な市場環境でのBUY提案 ---
    print("\n【シナリオ1: 穏やかな市場での『BUY』提案】")
    safe_market_data = {
        "price": 152.5, "volume": 150, "spread": 0.012,
        "volatility": 0.15, "historical_data": dummy_hist_data
    }
    safe_assessment = noctus_ai.assess(safe_market_data, "BUY")
    print(f"🛡️ ノクトゥスの最終判断: {safe_assessment['decision']} (理由: {safe_assessment['reason']})")

    # --- シナリオ2: ボラティリティ過大でのSELL提案 ---
    print("\n【シナリオ2: 荒れ狂う市場での『SELL』提案】")
    volatile_market_data = {
        "price": 148.0, "volume": 200, "spread": 0.015,
        "volatility": 0.3, "historical_data": dummy_hist_data
    }
    volatile_assessment = noctus_ai.assess(volatile_market_data, "SELL")
    print(f"🛡️ ノクトゥスの最終判断: {volatile_assessment['decision']} (理由: {volatile_assessment['reason']})")

    # --- シナリオ3: VaRリスクが高い状況でのBUY提案 ---
    print("\n【シナリオ3: VaRリスクが高い市場での『BUY』提案】")
    risky_hist_data = pd.DataFrame({
        'Close': np.concatenate([np.random.normal(150, 1, 90), np.random.normal(140, 5, 10)])
    })
    risky_hist_data['returns'] = risky_hist_data['Close'].pct_change().dropna()
    var_risk_market_data = {
        "price": 145.0, "volume": 200, "spread": 0.015,
        "volatility": 0.20, "historical_data": risky_hist_data
    }
    var_risk_assessment = noctus_ai.assess(var_risk_market_data, "BUY")
    print(f"🛡️ ノクトゥスの最終判断: {var_risk_assessment['decision']} (理由: {var_risk_assessment['reason']})")

    logging.info("--- リスク管理官ノクトゥス、単独試練の儀を完了 ---")
