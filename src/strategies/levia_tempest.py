#!/usr/bin/env python3
# coding: utf-8

"""
⚡ Levia Tempest (v2.1)
- 高速反応型スキャルピングAI
- 価格の微細な変動を捉え、短期的な売買判断を専門とする
- 流動性やスプレッドを常に監視し、好機のみを狙う
"""

import logging
from typing import Dict, Optional

# --- 王国の基盤モジュールをインポート ---
# MarketDataFetcherは現時点では直接使用しないが、将来的な拡張のため残す
from src.core.data_loader import MarketDataFetcher
from src.core.risk_manager import RiskManager # 簡易的なリスクチェックに利用

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')


class LeviaTempest:
    """
    市場の嵐の中、瞬きの間に好機を見出すスキャルピングAI。
    """

    def __init__(self, price_threshold: float = 0.0005, min_liquidity: float = 120, max_spread: float = 0.018, max_volatility: float = 0.2):
        """
        コンストラクタ。スキャルピング判断のための閾値を設定する。
        """
        self.price_threshold = price_threshold
        self.min_liquidity = min_liquidity
        self.max_spread = max_spread
        self.max_volatility = max_volatility
        # Leviaは独立したリスク評価も担う
        self.risk_manager = RiskManager()
        logging.info("スキャルピングAIレビア、戦場に到着しました。嵐の前の静けさ…好機を待ちます。")

    def _calculate_price_change(self, market_data: Dict) -> float:
        """現在価格と直前価格の差分を返す"""
        return market_data.get("price", 0.0) - market_data.get("previous_price", 0.0)

    def propose(self, market_data: Dict) -> Dict:
        """
        王Noctriaへの献上：現在の市場状況に基づくスキャルピング判断を返す
        """
        logging.info("瞬間の好機を探るため、市場の微細な動きを観測します…")

        try:
            liquidity = market_data["volume"]
            spread = market_data["spread"]
            volatility = market_data["volatility"]
            price_change = self._calculate_price_change(market_data)
        except KeyError as e:
            logging.error(f"市場データの欠損により判断不能。今は動くべき時ではありません。欠損キー: {e}")
            return self._create_proposal("HOLD", 0.0, market_data)

        # --- スキャルピング実行の前提条件チェック ---
        if liquidity < self.min_liquidity:
            logging.warning(f"市場の活気なし（流動性: {liquidity} < {self.min_liquidity}）。見送ります。")
            return self._create_proposal("HOLD", 0.0, market_data)

        if spread > self.max_spread:
            logging.warning(f"霧が深いようです（スプレッド: {spread} > {self.max_spread}）。見送ります。")
            return self._create_proposal("HOLD", 0.0, market_data)
            
        if volatility > self.max_volatility:
            logging.warning(f"嵐が激しすぎます（ボラティリティ: {volatility} > {self.max_volatility}）。見送ります。")
            return self._create_proposal("HOLD", 0.0, market_data)
        
        # --- スキャルピング判断 ---
        score = min(abs(price_change) / (self.price_threshold + 1e-9), 1.0) # 閾値に対する価格変動の大きさでスコア付け

        if price_change > self.price_threshold:
            signal = "BUY"
            logging.info(f"上昇の兆し！判断: {signal} (スコア: {score:.2f})")
        elif price_change < -self.price_threshold:
            signal = "SELL"
            logging.info(f"下降の兆し！判断: {signal} (スコア: {score:.2f})")
        else:
            signal = "HOLD"
            logging.info("好機見当たらず。静観します。")
            score = 0.0 # HOLDの場合はスコア0

        return self._create_proposal(signal, score, market_data)

    def _create_proposal(self, signal: str, score: float, market_data: Dict) -> Dict:
        """提案用の辞書を作成するヘルパー関数"""
        return {
            "name": "LeviaTempest",
            "type": "scalping_signal",
            "signal": signal,
            "confidence": round(score, 4),
            "symbol": market_data.get("symbol", "USDJPY"),
            "priority": "very_high" # スキャルピングは即時性が命
        }

# ========================================
# ✅ 単体テスト＆実行ブロック
# ========================================
if __name__ == "__main__":
    logging.info("--- スキャルピングAIレビア、単独試練の儀を開始 ---")
    levia_ai = LeviaTempest(price_threshold=0.0005)

    # --- シナリオ1: 買いシグナル ---
    print("\n【シナリオ1: 僅かな上昇の好機】")
    buy_market_data = {
        "price": 1.2050, "previous_price": 1.2044, "volume": 150,
        "spread": 0.012, "volatility": 0.15, "symbol": "USDJPY"
    }
    buy_proposal = levia_ai.propose(buy_market_data)
    print(f"⚡ レヴィアの進言: {buy_proposal}")

    # --- シナリオ2: 売りシグナル ---
    print("\n【シナリオ2: 僅かな下降の好機】")
    sell_market_data = {
        "price": 1.2040, "previous_price": 1.2048, "volume": 200,
        "spread": 0.010, "volatility": 0.18, "symbol": "USDJPY"
    }
    sell_proposal = levia_ai.propose(sell_market_data)
    print(f"⚡ レヴィアの進言: {sell_proposal}")
    
    # --- シナリオ3: 条件を満たさずHOLD ---
    print("\n【シナリオ3: 嵐が激しすぎる市場】")
    hold_market_data = {
        "price": 1.2050, "previous_price": 1.2040, "volume": 200,
        "spread": 0.015, "volatility": 0.3, # ボラティリティが高すぎる
        "symbol": "USDJPY"
    }
    hold_proposal = levia_ai.propose(hold_market_data)
    print(f"⚡ レヴィアの進言: {hold_proposal}")

    logging.info("\n--- スキャルピングAIレビア、単独試練の儀を完了 ---")
