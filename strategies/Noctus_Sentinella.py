import numpy as np
from data.market_data_fetcher import MarketDataFetcher
from core.risk_management import RiskManagement  # ✅ 修正済み

class NoctusSentinella:
    """リスク管理と異常検知を行うAI（改修版）"""
    
    def __init__(self, risk_threshold=0.02, max_spread=0.018, min_liquidity=120):
        self.risk_threshold = risk_threshold  # 許容リスクレベル
        self.max_spread = max_spread  # 最大許容スプレッド
        self.min_liquidity = min_liquidity  # 最低市場流動性
        self.market_fetcher = MarketDataFetcher(api_key="YOUR_API_KEY")
        self.risk_manager = RiskManagement()  # ✅ クラス名修正済み

    def process(self, market_data):
        """市場データを分析し、リスクを評価"""
        risk_score = self._calculate_risk(market_data)
        spread = market_data["spread"]
        liquidity = market_data["volume"]
        order_block_impact = market_data["order_block"]
        volatility = market_data["volatility"]

        # 流動性とスプレッドのチェック
        if liquidity < self.min_liquidity or spread > self.max_spread:
            return "AVOID_TRADING"

        # ボラティリティと大口注文の影響を考慮し、リスク評価を強化
        adjusted_risk_threshold = self.risk_threshold * (1 + order_block_impact)
        
        if risk_score > adjusted_risk_threshold and volatility > 0.2:
            return "REDUCE_RISK"
        else:
            return "MAINTAIN_POSITION"

    def _calculate_risk(self, market_data):
        """市場データからリスクスコアを計算（VaR適用）"""
        price_changes = market_data["price_history"]
        volatility = np.std(price_changes)
        risk_value = self.risk_manager.calculate_var(price_changes)
        return risk_value / market_data["price"]

# ✅ 改修後のリスク管理テスト
if __name__ == "__main__":
    noctus_ai = NoctusSentinella()
    mock_market_data = {
        "price": 1.2530, "price_history": [1.2500, 1.2525, 1.2550, 1.2510, 1.2540],
        "spread": 0.015, "volume": 120, "order_block": 0.5, "volatility": 0.22
    }
    risk_decision = noctus_ai.process(mock_market_data)
    print("Risk Management Decision:", risk_decision)
