import numpy as np
from core.NoctriaEnv import NoctriaEnv
from strategies.reinforcement.dqn_agent import DQNAgent


def run_dqn_training(episodes=100, epsilon=0.1):
    # 環境 & エージェント初期化
    env = NoctriaEnv()
    agent = DQNAgent(state_dim=env.state_dim, action_dim=len(env.action_space))

    for episode in range(episodes):
        state = env.reset()
        done = False
        total_reward = 0

        while not done:
            # 行動を決定
            action_idx = agent.decide_action(state, epsilon=epsilon)
            action = env.action_space[action_idx]

            # 環境ステップ
            next_state, reward, done, _ = env.step(action)
            total_reward += reward

            # 経験をリプレイなしの簡易版で即座に学習
            experience = (
                np.expand_dims(state, axis=0),  # 状態
                [action_idx],                   # 行動（整数）
                [reward],                       # 報酬
                np.expand_dims(next_state, axis=0),  # 次状態
                [done]                          # エピソード終了フラグ
            )
            agent.update(experience)

            state = next_state

        print(f"[Episode {episode+1}] Total Reward: {total_reward:.4f}")

    print("✅ 強化学習トレーニング完了！")


# ✅ テスト実行例
if __name__ == "__main__":
    run_dqn_training(episodes=10, epsilon=0.1)
