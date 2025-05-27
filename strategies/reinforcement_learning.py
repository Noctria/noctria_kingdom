import numpy as np

class ReinforcementLearning:
    """強化学習を用いた市場適応型戦略設計"""
    
    def __init__(self, learning_rate=0.01, discount_factor=0.9):
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.q_table = {}  # 状態とアクションの価値を保持

    def process(self, market_state):
        """市場データをもとに最適戦略を決定"""
        action = self._select_action(market_state)
        reward = self._calculate_reward(market_state, action)
        self._update_q_table(market_state, action, reward)
        return action

    def _select_action(self, market_state):
        """最適なアクションを選択"""
        if market_state in self.q_table:
            return max(self.q_table[market_state], key=self.q_table[market_state].get)
        return "HOLD"

    def _calculate_reward(self, market_state, action):
        """市場データに基づいて報酬を算出"""
        return np.random.uniform(-1, 1)  # 仮の報酬関数

    def _update_q_table(self, market_state, action, reward):
        """Qテーブルを更新"""
        if market_state not in self.q_table:
            self.q_table[market_state] = {}
        self.q_table[market_state][action] = reward + self.discount_factor * np.max(list(self.q_table[market_state].values()))

# ✅ 強化学習適用テスト
if __name__ == "__main__":
    rl_agent = ReinforcementLearning()
    mock_market_state = "Bullish"
    decision = rl_agent.process(mock_market_state)
    print("Reinforcement Learning Decision:", decision)
