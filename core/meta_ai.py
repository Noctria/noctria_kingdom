import numpy as np

class MetaAI:
    """
    MetaAI:
    Noctria全体の各戦略AIの出力を集約し、最終的なトレード意思決定を行う統合AI。
    さらに強化学習ベースのフィードバックループを持ち、戦略を継続的に改善する。
    """

    def __init__(self, strategy_agents):
        """
        strategy_agents: dict
            各戦略エージェント（例: {'Aurus': AurusSingularis(), 'Levia': LeviaTempest(), ...}）
        """
        self.strategy_agents = strategy_agents
        # 例: 将来的に強化学習モデルやQテーブルの初期化をここで行う
        self.q_table = {}  # 例としての初期化
        self.epsilon = 0.1  # ε-greedy探索率（将来的に拡張）
        self.learning_rate = 0.01
        self.discount_factor = 0.95

    def decide_final_action(self, market_state):
        """
        各戦略の出力を集約し、最終的なアクションを決定する
        """
        # 各戦略AIからアクションを取得
        strategy_actions = {}
        for name, agent in self.strategy_agents.items():
            if hasattr(agent, "process"):
                action = agent.process(market_state)
            else:
                print(f"⚠️ {name} のエージェントが process メソッドを持っていません。HOLDを返します")
                action = "HOLD"
            strategy_actions[name] = action

        # 単純多数決（例：SELLが多い場合SELL）
        action_counts = {a: list(strategy_actions.values()).count(a) for a in ["BUY", "SELL", "HOLD", "AVOID_TRADING", "REDUCE_RISK"]}
        final_action = max(action_counts, key=action_counts.get)

        print(f"[MetaAI] Strategy actions: {strategy_actions}")
        print(f"[MetaAI] Final action: {final_action}")

        return final_action

    def learn(self, state, action, reward, next_state, done):
        """
        簡易的な強化学習の学習ステップ（例: Qテーブル更新）
        将来的にDQN/PPOなどと差し替え可能
        """
        state_key = tuple(state.tolist())
        next_state_key = tuple(next_state.tolist())

        # Qテーブル初期化
        if state_key not in self.q_table:
            self.q_table[state_key] = {a: 0.0 for a in ["BUY", "SELL", "HOLD"]}
        if next_state_key not in self.q_table:
            self.q_table[next_state_key] = {a: 0.0 for a in ["BUY", "SELL", "HOLD"]}

        # TDターゲット計算
        best_next_q = max(self.q_table[next_state_key].values())
        td_target = reward + self.discount_factor * best_next_q * (0 if done else 1)
        td_error = td_target - self.q_table[state_key][action]

        # Q値更新
        self.q_table[state_key][action] += self.learning_rate * td_error

        print(f"[MetaAI] Q-value updated for state={state_key}, action={action}, new_value={self.q_table[state_key][action]:.4f}")

# ✅ テスト例
if __name__ == "__main__":
    # ダミー戦略AI群
    class DummyAI:
        def process(self, market_data):
            return np.random.choice(["BUY", "SELL", "HOLD"])

    strategy_agents = {
        "Aurus": DummyAI(),
        "Levia": DummyAI(),
        "Noctus": DummyAI(),
        "Prometheus": DummyAI()
    }

    meta_ai = MetaAI(strategy_agents)
    mock_market_data = {"price": 1.2345, "volume": 1000}
    action = meta_ai.decide_final_action(mock_market_data)

    # 強化学習テスト
    state = np.random.rand(12)
    next_state = np.random.rand(12)
    meta_ai.learn(state, action="BUY", reward=0.5, next_state=next_state, done=False)
