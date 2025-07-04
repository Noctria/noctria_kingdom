# tests/test_meta_ai_rl.py

import numpy as np
from core.meta_ai import MetaAI
from strategies.Aurus_Singularis import AurusSingularis
from strategies.Levia_Tempest import LeviaTempest
from strategies.Noctus_Sentinella import NoctusSentinella
from strategies.Prometheus_Oracle import PrometheusOracle

def main():
    print("✅ MetaAI統合PPO強化学習テスト開始！")

    # 戦略AIインスタンスを生成
    strategy_agents = {
        "Aurus": AurusSingularis(),
        "Levia": LeviaTempest(),
        "Noctus": NoctusSentinella(),
        "Prometheus": PrometheusOracle()
    }

    # MetaAIに戦略AI群を渡して初期化
    meta_ai = MetaAI(strategy_agents=strategy_agents)

    # 簡易テスト（各ステップのアクション・報酬を見ておく）
    num_episodes = 10
    for episode in range(num_episodes):
        obs = meta_ai.reset()
        done = False
        total_reward = 0

        for step in range(10):  # 簡易: 10ステップ
            action = meta_ai.decide_final_action({"observation": obs})
            obs, reward, done, _ = meta_ai.step(action)
            total_reward += reward
            print(f"Episode {episode + 1} | Step {step + 1} | Action: {action} | Reward: {reward:.2f}")

        print(f"Episode {episode + 1} | Total Reward: {total_reward:.2f}")
        print("------------------------------------------")

    # PPOによる本格的な学習サイクルを1度走らせておく
    meta_ai.learn(total_timesteps=2048)

    print("✅ MetaAI統合PPO強化学習テスト完了！")

if __name__ == "__main__":
    main()
