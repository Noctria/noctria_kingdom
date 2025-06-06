import numpy as np
from core.NoctriaEnv import NoctriaEnv
from strategies.reinforcement.dqn_agent import DQNAgent
from strategies.reinforcement.experience_replay import ExperienceReplay


def run_dqn_training(episodes=100, epsilon=0.1, batch_size=32):
    env = NoctriaEnv()
    agent = DQNAgent(state_dim=env.state_dim, action_dim=len(env.action_space))
    replay = ExperienceReplay(capacity=10000)

    for episode in range(episodes):
        state = env.reset()
        done = False
        total_reward = 0

        while not done:
            # 行動選択
            action_idx = agent.decide_action(state, epsilon=epsilon)
            action = env.action_space[action_idx]

            # 環境ステップ
            next_state, reward, done, _ = env.step(action)
            total_reward += reward

            # 経験を保存（addに統一！）
            replay.add(state, action_idx, reward, next_state, done)

            # 充分に溜まったら学習
            if replay.size() > batch_size:
                batch = replay.sample(batch_size)
                agent.update(batch)

            state = next_state

        print(f"[Episode {episode+1}] Total Reward: {total_reward:.4f}")

    print("✅ 強化学習トレーニング完了（ExperienceReplay版・add統一）")


# ✅ テスト実行
if __name__ == "__main__":
    run_dqn_training(episodes=10, epsilon=0.1, batch_size=32)
