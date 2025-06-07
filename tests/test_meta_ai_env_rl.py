# tests/test_meta_ai_env_rl.py

import gym
from stable_baselines3 import PPO
from core.meta_ai_env import MetaAIEnv

def main():
    print("✅ MetaAI統合強化学習テスト開始")

    # ✅ 環境初期化
    env = MetaAIEnv()

    # ✅ PPOエージェント初期化
    model = PPO("MlpPolicy", env, verbose=1)

    # ✅ 簡易的に学習
    model.learn(total_timesteps=10000)

    # ✅ 環境の動作テスト
    obs = env.reset()
    for _ in range(10):
        action, _states = model.predict(obs, deterministic=True)
        obs, reward, done, _ = env.step(action)
        print(f"Action: {action}, Reward: {reward}, Done: {done}")
        if done:
            obs = env.reset()

    print("✅ MetaAI統合強化学習テスト完了！")

if __name__ == "__main__":
    main()
