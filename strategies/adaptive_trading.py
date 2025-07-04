import numpy as np
import random

class AdaptiveTrading:
    """
    自己進化型トレード戦略 - 強化学習に基づくリアルタイム最適化

    状態: 市場データ（例：インジケータやインジケータ群）
    アクション: 取引シグナル（例：SELL, HOLD, BUY）
    """
    def __init__(self, state_size, action_size, learning_rate=0.01, discount_factor=0.99,
                 exploration_rate=1.0, exploration_decay=0.995, min_exploration=0.01):
        self.state_size = state_size
        self.action_size = action_size
        self.lr = learning_rate              # Q値更新の学習率
        self.gamma = discount_factor         # 割引率
        self.epsilon = exploration_rate      # ランダム探索の初期確率
        self.epsilon_decay = exploration_decay
        self.epsilon_min = min_exploration
        # Qテーブル：各状態（ハッシュ可能なキー）ごとにアクションごとの期待値の配列を保存
        self.q_table = {}

    def get_state_key(self, state):
        """状態をハッシュ可能なキーに変換（小数点以下2桁に丸め）"""
        return tuple(np.round(state, decimals=2))

    def choose_action(self, state):
        """ε-グリーディ戦略によりアクションを選択"""
        state_key = self.get_state_key(state)
        if state_key not in self.q_table:
            self.q_table[state_key] = np.zeros(self.action_size)
        # ランダム探索: ε の確率でランダムなアクションを選択
        if random.uniform(0, 1) < self.epsilon:
            action = random.randint(0, self.action_size - 1)
        else:
            action = int(np.argmax(self.q_table[state_key]))
        return action

    def update(self, state, action, reward, next_state, done):
        """Q学習の更新公式に基づいて Qテーブルを更新"""
        state_key = self.get_state_key(state)
        next_state_key = self.get_state_key(next_state)

        if state_key not in self.q_table:
            self.q_table[state_key] = np.zeros(self.action_size)
        if next_state_key not in self.q_table:
            self.q_table[next_state_key] = np.zeros(self.action_size)

        # 目標値の算出
        target = reward
        if not done:
            target += self.gamma * np.max(self.q_table[next_state_key])
        # Q値の更新
        self.q_table[state_key][action] += self.lr * (target - self.q_table[state_key][action])
        
        # 探索率の減衰
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

    def preprocess(self, market_data):
        """
        市場データを前処理して状態ベクトルに変換
        ※ここではシンプルな正規化（最大値で割る）を実施。必要に応じて拡張する。
        """
        state = np.array(market_data, dtype=float)
        if state.max() > 0:
            state = state / state.max()
        return state

    def act(self, market_data):
        """
        市場データをもとにアクションを選択
        戻り値: (選択アクション, 前処理済み状態ベクトル)
        """
        state = self.preprocess(market_data)
        action = self.choose_action(state)
        return action, state

    def train(self, market_data, reward, next_market_data, done=False):
        """
        学習プロセス: 現在の状態、報酬、次の状態から Qテーブルを更新し、
        アクションを出力する
        """
        state = self.preprocess(market_data)
        next_state = self.preprocess(next_market_data)
        action = self.choose_action(state)
        self.update(state, action, reward, next_state, done)
        return action

# ✅ シンプルなテストシミュレーション
if __name__ == "__main__":
    # 状態サイズ: 3次元の市場指標。アクション: 0=SELL, 1=HOLD, 2=BUY
    agent = AdaptiveTrading(state_size=3, action_size=3)
    
    # ダミーなシミュレーションループ（100エピソード）
    for episode in range(1, 101):
        # 市場状態の生成（例: ランダムな3要素のベクトル）
        current_market = np.random.rand(3) * 100
        next_market = np.random.rand(3) * 100
        # 報酬は簡易的にランダム（実際は戦略の収益やリスク評価を反映）
        reward = np.random.uniform(-1, 1)
        done = random.choice([False, True])
        action = agent.train(current_market, reward, next_market, done)
        print(f"Episode {episode:03d} | Action: {action} | Reward: {reward:.3f} | Epsilon: {agent.epsilon:.3f}")
