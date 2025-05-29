import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from data_loader import MarketDataFetcher

class NoctriaRL(nn.Module):
    """市場適応型強化学習モデル（最適化アルゴリズム導入）"""

    def __init__(self, state_size, action_size):
        super(NoctriaRL, self).__init__()
        self.fc1 = nn.Linear(state_size, 256)
        self.fc2 = nn.Linear(256, 128)
        self.fc3 = nn.Linear(128, 64)
        self.fc4 = nn.Linear(64, action_size)

    def forward(self, state):
        x = torch.relu(self.fc1(state))
        x = torch.relu(self.fc2(x))
        x = torch.relu(self.fc3(x))
        return self.fc4(x)

class RLTrainer:
    """市場データを活用したAIトレーダーの学習強化"""

    def __init__(self, market_fetcher):
        self.market_fetcher = market_fetcher
        self.state_size = 5
        self.action_size = 4
        self.model = NoctriaRL(self.state_size, self.action_size)

        # 最適化アルゴリズムを AdamW に変更
        self.optimizer = optim.AdamW(self.model.parameters(), lr=0.001, weight_decay=0.01)
        
        self.gamma = 0.99  # 割引率
        self.epsilon = 1.0  # 探索率
        self.epsilon_decay = 0.97  # 探索率減衰
        self.epsilon_min = 0.05  # 最小探索率

    def train_step(self):
        """市場データを取得し、強化学習モデルに適用"""
        market_data = self.market_fetcher.fetch_data()
        if "error" in market_data:
            return "Market data fetch failed."

        state = torch.tensor([market_data["price"], market_data["volatility"], market_data["trend_strength"], market_data["news_sentiment"], 1], dtype=torch.float32)
        action_probs = self.model(state)

        best_action = torch.argmax(action_probs).item()
        reward = self.calculate_reward(best_action, market_data)

        # 最適化戦略適用
        loss = -reward  
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        # 探索率の動的調整（市場環境に応じた変動）
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

        return f"Trained AI with best action: {best_action}, Reward: {reward}"

    def calculate_reward(self, action, market_data):
        """市場状況に応じた報酬関数（リスク管理を強化）"""
        profit = np.random.uniform(0, 1) if action == 0 else np.random.uniform(-0.5, 0.8)
        risk_penalty = -abs(np.random.uniform(0, 0.3))  # リスク要素を追加
        stability_factor = 1 if np.random.uniform(0, 1) > 0.5 else -1
        return profit + risk_penalty + stability_factor

# ✅ AIモデルのトレーニング実行
if __name__ == "__main__":
    api_key = "YOUR_API_KEY"
    market_fetcher = MarketDataFetcher(api_key)
    trainer = RLTrainer(market_fetcher)

    for _ in range(100):  # 学習回数を増やし、収束の安定性を強化
        result = trainer.train_step()
        print(result)
