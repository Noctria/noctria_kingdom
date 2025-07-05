import numpy as np
from core.data.market_data_fetcher import MarketDataFetcher  # ✅ パス修正済み
from core.risk_manager import RiskManager  # ✅ リスク管理モジュール

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
        self.market_fetcher = MarketDataFetcher()  # APIキーは不要（yfinance）
        self.risk_manager = RiskManager()

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

        # ボラティリティ・大口注文影響を考慮した閾値補正
        adjusted_threshold = self.threshold * (1 + order_block_impact)

        print(f"[Levia] 📊 price_change={price_change:.5f}, liquidity={liquidity}, spread={spread}, volatility={volatility}, threshold={adjusted_threshold:.5f}")

        # ✅ 基本チェック（流動性・スプレッド）
        if liquidity < self.min_liquidity or spread > self.max_spread:
            print("[Levia] ⚠️ 流動性不足またはスプレッド超過 → HOLD")
            return "HOLD"

        # ✅ 異常検知フィルター
        if self.risk_manager.detect_anomalies():
            print("[Levia] 🛡️ リスク検知 → HOLD")
            return "HOLD"

        # ✅ トレード判断
        if price_change > adjusted_threshold and volatility < 0.2:
            return "BUY"
        elif price_change < -adjusted_threshold and volatility < 0.2:
            return "SELL"
        else:
            return "HOLD"

    def _calculate_price_change(self, market_data):
        """
        現在価格と直前価格の差分を返す
        """
        return market_data["price"] - market_data["previous_price"]

# ✅ 単体テスト
if __name__ == "__main__":
    levia_ai = LeviaTempest()
    mock_market_data = {
        "price": 1.2050,
        "previous_price": 1.2040,
        "volume": 150,
        "spread": 0.012,
        "order_block": 0.4,
        "volatility": 0.15
    }
    decision = levia_ai.process(mock_market_data)
    print("Scalping Decision:", decision)
