import numpy as np
from core.data.market_data_fetcher import MarketDataFetcher
from core.risk_manager import RiskManager

class LeviaTempest:
    """
    ⚡ 高速反応型スキャルピングAI（Levia Tempest）  
    - 価格の変動・流動性・スプレッド・ボラティリティをもとに瞬時のトレード判断を行う。
    - RiskManager による異常検知で安全性を担保。
    """

    def __init__(self, threshold=0.05, min_liquidity=120, max_spread=0.018):
        self.threshold = threshold
        self.min_liquidity = min_liquidity
        self.max_spread = max_spread
        self.market_fetcher = MarketDataFetcher()
        self.risk_manager = RiskManager()

    def _calculate_price_change(self, market_data):
        """現在価格と直前価格の差分を返す"""
        return market_data["price"] - market_data["previous_price"]

    def process(self, market_data):
        """
        入力された市場データに対してトレード戦略を実行し、BUY/SELL/HOLDを返す。
        """
        try:
            price_change = self._calculate_price_change(market_data)
            liquidity = market_data["volume"]
            spread = market_data["spread"]
            order_block_impact = market_data["order_block"]
            volatility = market_data["volatility"]
        except KeyError as e:
            print(f"[Levia] ⚠️ 入力データ欠損: {e}")
            return "HOLD"

        adjusted_threshold = self.threshold * (1 + order_block_impact)

        print(f"[Levia] 📊 price_change={price_change:.5f}, liquidity={liquidity}, spread={spread}, volatility={volatility}, threshold={adjusted_threshold:.5f}")

        if liquidity < self.min_liquidity or spread > self.max_spread:
            print("[Levia] ⚠️ 流動性不足またはスプレッド超過 → HOLD")
            return "HOLD"

        if self.risk_manager.detect_anomalies():
            print("[Levia] 🛡️ リスク検知 → HOLD")
            return "HOLD"

        if price_change > adjusted_threshold and volatility < 0.2:
            return "BUY"
        elif price_change < -adjusted_threshold and volatility < 0.2:
            return "SELL"
        else:
            return "HOLD"

    def propose(self, market_data: dict) -> dict:
        """
        📩 王Noctriaへの献上：高速判断に基づく戦略提案を返す
        """
        try:
            price_change = self._calculate_price_change(market_data)
            liquidity = market_data["volume"]
            spread = market_data["spread"]
            order_block_impact = market_data["order_block"]
            volatility = market_data["volatility"]
        except KeyError as e:
            print(f"[Levia] ⚠️ 入力データ欠損（propose）: {e}")
            return {
                "name": "Levia",
                "type": "scalping",
                "signal": "HOLD",
                "score": 0.0,
                "symbol": market_data.get("symbol", "USDJPY"),
                "priority": "high"
            }

        adjusted_threshold = self.threshold * (1 + order_block_impact)

        # 初期スコア（price_change の絶対値とボラティリティに基づく簡易スコア）
        raw_score = min(abs(price_change) / (adjusted_threshold + 1e-6), 1.0)
        score = round(raw_score * (1 - volatility), 3)  # ボラティリティが低いほどスコア↑

        if liquidity < self.min_liquidity or spread > self.max_spread:
            signal = "HOLD"
        elif self.risk_manager.detect_anomalies():
            signal = "HOLD"
        elif price_change > adjusted_threshold and volatility < 0.2:
            signal = "BUY"
        elif price_change < -adjusted_threshold and volatility < 0.2:
            signal = "SELL"
        else:
            signal = "HOLD"

        return {
            "name": "Levia",
            "type": "scalping",
            "signal": signal,
            "score": score,
            "symbol": market_data.get("symbol", "USDJPY"),
            "priority": "high"
        }

# ✅ スタンドアロンテスト
if __name__ == "__main__":
    levia_ai = LeviaTempest()
    mock_market_data = {
        "price": 1.2050,
        "previous_price": 1.2040,
        "volume": 150,
        "spread": 0.012,
        "order_block": 0.4,
        "volatility": 0.15,
        "symbol": "USDJPY"
    }
    result = levia_ai.propose(mock_market_data)
    print("👑 王への提案（Levia）:", result)
