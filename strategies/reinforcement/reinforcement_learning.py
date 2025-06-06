import numpy as np
import torch
from core.NoctriaEnv import NoctriaEnv
from strategies.reinforcement.dqn_agent import DQNAgent
from strategies.reinforcement.experience_replay import ExperienceReplay


def run_dqn_training(episodes=100, epsilon=0.1, batch_size=32, save_path="logs/dqn_model.pth"):
    env = NoctriaEnv()
    agent = DQNAgent(state_dim=env.state_dim, action_dim=len(env.action_space))
    replay = ExperienceReplay(capacity=10000)

    for episode in range(episodes):
        state = env.reset()
        done = False
        total_reward = 0

        while not done:
            action_idx = agent.decide_action(state, epsilon=epsilon)
            action = env.action_space[action_idx]
            next_state, reward, done, _ = env.step(action)
            total_reward += reward

            replay.add(state, action_idx, reward, next_state, done)

            if replay.size() > batch_size:
                batch = replay.sample(batch_size)
                agent.update(batch)

            state = next_state

        print(f"[Episode {episode+1}] Total Reward: {total_reward:.4f}")

    # ✅ 学習済みモデルを保存
    torch.save(agent.model.state_dict(), save_path)
    print(f"✅ モデルを保存しました: {save_path}")


def load_trained_model(agent, load_path="logs/dqn_model.pth"):
    agent.model.load_state_dict(torch.load(load_path))
    agent.model.eval()
    print(f"✅ モデルをロードしました: {load_path}")


# ✅ テスト実行
if __name__ == "__main__":
    run_dqn_training(episodes=10, epsilon=0.1, batch_size=32)
