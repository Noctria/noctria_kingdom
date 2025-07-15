#!/usr/bin/env python3
# coding: utf-8

"""
🛡️ Levia Tempest (v2.0)
- 市場のリスクを評価し、最終的な実行可否を判断するリスク管理官AI
- 流動性、スプレッド、ボラティリティ、異常検知など複数の観点からリスクを評価する
"""

import logging
from typing import Dict, Optional

# --- 王国の基盤モジュールをインポート ---
from src.core.data_loader import MarketDataFetcher
from src.core.risk_manager import RiskManager

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')


class LeviaTempest:
    """
    市場の嵐を鎮める守護者。提案された戦略のリスクを評価し、最終的な承認または拒否権を発動する。
    """

    def __init__(self, min_liquidity: float = 120, max_spread: float = 0.018, max_volatility: float = 0.2):
        """
        コンストラクタ。リスク評価のための閾値を設定する。
        """
        self.min_liquidity = min_liquidity
        self.max_spread = max_spread
        self.max_volatility = max_volatility
        self.risk_manager = RiskManager()
        logging.info("リスク管理官レビア、着任しました。王国の盾とならんことを。")

    def assess_risk(self, market_data: Dict, proposed_action: str) -> Dict:
        """
        市場データと提案されたアクションに基づき、リスクを評価し最終判断を下す。
        判断は 'APPROVE' (承認) または 'VETO' (拒否) とする。
        """
        logging.info(f"進言『{proposed_action}』に対するリスク評価を開始します。")

        # HOLDの提案であれば、リスク評価の必要なく承認
        if proposed_action == "HOLD":
            logging.info("行動『HOLD』は承認されました。市場は静観が賢明です。")
            return {"decision": "APPROVE", "reason": "No action proposed."}

        try:
            liquidity = market_data["volume"]
            spread = market_data["spread"]
            volatility = market_data["volatility"]
        except KeyError as e:
            logging.error(f"市場データの欠損により評価不能。安全のため拒否します。欠損キー: {e}")
            return {"decision": "VETO", "reason": f"Missing market data: {e}"}

        # 1. 流動性の評価
        if liquidity < self.min_liquidity:
            reason = f"流動性不足（現在値: {liquidity} < 閾値: {self.min_liquidity}）。市場が枯渇しています。"
            logging.warning(f"【拒否】{reason}")
            return {"decision": "VETO", "reason": reason}

        # 2. スプレッドの評価
        if spread > self.max_spread:
            reason = f"スプレッド過大（現在値: {spread} > 閾値: {self.max_spread}）。取引コストが高すぎます。"
            logging.warning(f"【拒否】{reason}")
            return {"decision": "VETO", "reason": reason}
            
        # 3. ボラティリティの評価
        if volatility > self.max_volatility:
            reason = f"ボラティリティ過大（現在値: {volatility} > 閾値: {self.max_volatility}）。市場が荒れ狂っています。"
            logging.warning(f"【拒否】{reason}")
            return {"decision": "VETO", "reason": reason}

        # 4. 外部リスクマネージャーによる異常検知
        if self.risk_manager.detect_anomalies(market_data):
            reason = "外部リスクマネージャーが市場の異常を検知しました。未知の嵐の兆候です。"
            logging.warning(f"【拒否】{reason}")
            return {"decision": "VETO", "reason": reason}

        # 全てのリスク評価を通過
        logging.info("全てのリスク評価を通過。行動は承認されました。良き風が吹きますように。")
        return {"decision": "APPROVE", "reason": "All risk checks passed."}

# ========================================
# ✅ 単体テスト＆実行ブロック
# ========================================
if __name__ == "__main__":
    logging.info("--- リスク管理官レビア、単独試練の儀を開始 ---")
    levia_ai = LeviaTempest()

    # --- シナリオ1: 安全な市場環境でのBUY提案 ---
    print("\n【シナリオ1: 穏やかな市場での『BUY』提案】")
    safe_market_data = {
        "price": 1.2050, "previous_price": 1.2040, "volume": 150,
        "spread": 0.012, "order_block": 0.4, "volatility": 0.15,
        "symbol": "USDJPY"
    }
    safe_assessment = levia_ai.assess_risk(safe_market_data, "BUY")
    print(f"🛡️ レヴィアの最終判断: {safe_assessment['decision']} (理由: {safe_assessment['reason']})")

    # --- シナリオ2: 流動性不足でのBUY提案 ---
    print("\n【シナリオ2: 流動性不足の市場での『BUY』提案】")
    illiquid_market_data = {
        "price": 1.2050, "previous_price": 1.2040, "volume": 50, # 流動性が低い
        "spread": 0.012, "order_block": 0.4, "volatility": 0.15,
        "symbol": "USDJPY"
    }
    illiquid_assessment = levia_ai.assess_risk(illiquid_market_data, "BUY")
    print(f"🛡️ レヴィアの最終判断: {illiquid_assessment['decision']} (理由: {illiquid_assessment['reason']})")
    
    # --- シナリオ3: ボラティリティ過大でのSELL提案 ---
    print("\n【シナリオ3: 荒れ狂う市場での『SELL』提案】")
    volatile_market_data = {
        "price": 1.2050, "previous_price": 1.2060, "volume": 200,
        "spread": 0.015, "order_block": 0.4, "volatility": 0.3, # ボラティリティが高い
        "symbol": "USDJPY"
    }
    volatile_assessment = levia_ai.assess_risk(volatile_market_data, "SELL")
    print(f"🛡️ レヴィアの最終判断: {volatile_assessment['decision']} (理由: {volatile_assessment['reason']})")

    logging.info("\n--- リスク管理官レビア、単独試練の儀を完了 ---")
