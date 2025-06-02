import numpy as np

class ExplorationStrategy:
    """
    強化学習における探索戦略を管理
    - ε-greedy
    - UCB (Upper Confidence Bound)
    - Softmax Exploration
    """

    def __init__(self, action_dim, epsilon=1.0, epsilon_decay=0.995, min_epsilon=0.01, c_ucb=2.0, tau=1.0):
        """
        初期化
        :param action_dim: 行動の次元数
        :param epsilon: ε-greedy 初期値
        :param epsilon_decay: ε-greedy の減衰率
        :param min_epsilon: 最小 ε値
        :param c_ucb: UCB の探索係数
        :param tau: Softmax Exploration の温度パラメータ
        """
        self.action_dim = action_dim
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.min_epsilon = min_epsilon
        self.c_ucb = c_ucb
        self.tau = tau
        self.action_counts = np.zeros(action_dim)
        self.action_values = np.zeros(action_dim)

    def select_action(self, q_values, method="epsilon_greedy"):
        """
        指定した探索戦略に基づき行動を選択
        :param q_values: Q値リスト
        :param method: 使用する探索戦略 ["epsilon_greedy", "ucb", "softmax"]
        :return: 選択された行動
        """
        if method == "epsilon_greedy":
            return self.epsilon_greedy(q_values)
        elif method == "ucb":
            return self.ucb_selection()
        elif method == "softmax":
            return self.softmax_exploration(q_values)
        else:
            raise ValueError("Unknown exploration method")

    def epsilon_greedy(self, q_values):
        """
        ε-greedy に基づく行動選択
        """
        if np.random.rand() < self.epsilon:
            action = np.random.randint(self.action_dim)
        else:
            action = np.argmax(q_values)
        
        # εの減衰
        self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)
        return action

    def ucb_selection(self):
        """
        UCB (Upper Confidence Bound) に基づく行動選択
        """
        total_count = np.sum(self.action_counts) + 1e-5  # 計算の安定性を考慮
        ucb_values = self.action_values + self.c_ucb * np.sqrt(np.log(total_count) / (self.action_counts + 1e-5))
        action = np.argmax(ucb_values)
        self.action_counts[action] += 1
        return action

    def softmax_exploration(self, q_values):
        """
        Softmax に基づく探索戦略
        """
        exp_q = np.exp(q_values / self.tau)
        probs = exp_q / np.sum(exp_q)
        action = np.random.choice(self.action_dim, p=probs)
        return action
