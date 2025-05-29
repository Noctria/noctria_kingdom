import logging
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from data_loader import MarketDataFetcher
from risk_management import RiskManager

class DynamicEnsembleModel(nn.Module):
    """PPO・DQN・A3C のアンサンブルモデル（動的重み調整）"""

    def __init__(self, state_size, action_size):
        super(DynamicEnsembleModel, self).__init__()
        self.ppo_model = nn.Linear(state_size, action_size)
        self.dqn_model = nn.Linear(state_size, action_size)
        self.a3c_model = nn.Linear(state_size, action_size)

        self.weights = nn.Parameter(torch.tensor([0.4, 0.3, 0.3], dtype=torch.float32))  # 初期値

    def adjust_weights(self, market_data):
        """市場環境に応じた動的重み調整"""
        volatility = market_data["volatility"]
        trend_strength = market_data["trend_strength"]

        self.weights.data = torch.tensor([
            max(0.2, min(0.6, 0.4 - volatility * 0.5)),  
            max(0.2, min(0.6, 0.3 + trend_strength * 0.3)),  
            max(0.2, min(0.6, 0.3 + volatility * 0.2))
        ], dtype=torch.float32)

    def forward(self, state):
        ppo_output = torch.softmax(self.ppo_model(state), dim=-1)
        dqn_output = self.dqn_model(state)
        a3c_output = torch.softmax(self.a3c_model(state), dim=-1)

        ensemble_output = self.weights[0] * ppo_output + self.weights[1] * dqn_output + self.weights[2] * a3c_output
        return ensemble_output

class Noctria:
    """市場適応型アンサンブルAIトレーダー"""

    def __init__(self):
        self.logger = logging.getLogger("Noctria")
        self.logger.setLevel(logging.DEBUG)

        self.market_data_fetcher = MarketDataFetcher(api_key="YOUR_API_KEY")
        self.risk_manager = RiskManager()

        self.state_size = 5
        self.action_size = 4
        self.ensemble_model = DynamicEnsembleModel(self.state_size, self.action_size)
        self.optimizer = optim.Adam(self.ensemble_model.parameters(), lr=0.001)

    def analyze_market(self):
        """市場データを取得・分析し、AIへ適用"""
        market_data = self.market_data_fetcher.fetch_data()
        if "error" in market_data:
            self.logger.error("Failed to fetch market data")
            return None

        risk_evaluation = self.risk_manager.calculate_var([market_data["price_change"]])
        self.ensemble_model.adjust_weights(market_data)

        state = torch.tensor([market_data["price"], market_data["volatility"], market_data["trend_strength"], market_data["news_sentiment"], 1], dtype=torch.float32)

        strategy_scores = self.ensemble_model(state)
        optimal_strategy = torch.argmax(strategy_scores).item()

        return market_data, risk_evaluation, optimal_strategy

    def execute_trade(self):
        """市場分析結果を元に、適応戦略を適用"""
        market_data, risk_evaluation, optimal_strategy = self.analyze_market()
        if not market_data:
            return "Market analysis failed."

        self.logger.info(f"Executing trade using strategy: {optimal_strategy}")
        return f"Executing trade using: {optimal_strategy}"

# ✅ Noctria AIの起動
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    noctria_ai = Noctria()
    trade_decision = noctria_ai.execute_trade()
    print(trade_decision)
