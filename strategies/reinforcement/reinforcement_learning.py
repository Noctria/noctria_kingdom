import numpy as np

class ReinforcementLearning:
    """強化学習を用いた市場適応型戦略設計"""

    def __init__(self, learning_rate=0.01, discount_factor=0.9, epsilon=0.1):
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon  # ε-greedy 探索率
        self.q_table = {}  # 状態とアクションの価値を保持
        self.actions = ["BUY", "SELL", "HOLD"]

    def process(self, market_state):
        """市場データをもとに最適戦略を決定"""
        action = self._select_action(market_state)
        reward = self._calculate_reward(market_state, action)
        self._update_q_table(market_state, action, reward)
        return action

    def _select_action(self, market_state):
        """ε-greedy に基づき行動を選択"""
        if np.random.rand() < self.epsilon:
            return np.random.choice(self.actions)  # ランダム探索
        if market_state in self.q_table:
            return max(self.q_table[market_state], key=self.q_table[market_state].get)  # 最適行動
        return "HOLD"

    def _calculate_reward(self, market_state, action):
        """市場データに基づいて報酬を算出（仮設）"""
        if action == "BUY" and market_state == "Bullish":
            return 1  # 上昇相場での買いがプラス
        elif action == "SELL" and market_state == "Bearish":
            return 1  # 下落相場での売りがプラス
        elif action == "HOLD":
            return 0  # 保持する場合の報酬
        return -1  # 市場と逆の動きで損失

    def _update_q_table(self, market_state, action, reward):
        """Qテーブルを更新（状態遷移考慮）"""
        if market_state not in self.q_table:
            self.q_table[market_state] = {a: 0 for a in self.actions}

        max_next_q = np.max(list(self.q_table[market_state].values()))
        self.q_table[market_state][action] += self.learning_rate * (reward + self.discount_factor * max_next_q - self.q_table[market_state][action])

# ✅ 強化学習適用テスト
if __name__ == "__main__":
    rl_agent = ReinforcementLearning()
    mock_market_state = "Bullish"
    decision = rl_agent.process(mock_market_state)
    print("Reinforcement Learning Decision:", decision)
