import numpy as np

class NoctusSentinella:
    """リスク管理と異常検知を行うAI"""
    
    def __init__(self, risk_threshold=0.02):
        self.risk_threshold = risk_threshold  # 許容リスクレベル

    def process(self, market_data):
        """市場データを分析し、リスクを評価"""
        risk_score = self._calculate_risk(market_data)
        if risk_score > self.risk_threshold:
            return "REDUCE_RISK"
        else:
            return "MAINTAIN_POSITION"

    def _calculate_risk(self, market_data):
        """市場データからリスクスコアを計算"""
        volatility = np.std(market_data["price_history"])
        return volatility / market_data["price"]

# ✅ リスク管理適用
if __name__ == "__main__":
    noctus_ai = NoctusSentinella()
    mock_market_data = {"price": 1.2530, "price_history": [1.2500, 1.2525, 1.2550, 1.2510, 1.2540]}
    risk_decision = noctus_ai.process(mock_market_data)
    print("Risk Management Decision:", risk_decision)
