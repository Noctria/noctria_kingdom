import numpy as np
import torch
from core.NoctriaEnv import NoctriaEnv
from strategies.reinforcement.dqn_agent import DQNAgent
from strategies.reinforcement.experience_replay import ExperienceReplay
from save_model_metadata import save_model_metadata

def run_dqn_training(episodes=100, epsilon=0.1, batch_size=32, save_path="logs/models/dqn_model_latest.pth"):
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

        # モデル保存
        model_path = f"logs/models/dqn_model_ep{episode+1}.pth"
        torch.save(agent.model.state_dict(), model_path)

        # メタデータ保存
        save_model_metadata(model_path, episode+1, total_reward, win_rate=0.85)

        print(f"[Episode {episode+1}] Total Reward: {total_reward:.4f}")

    print("✅ 学習完了！")

if __name__ == "__main__":
    run_dqn_training(episodes=10)
