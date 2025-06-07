#!/usr/bin/env python3
# coding: utf-8

import gym
import numpy as np
from stable_baselines3 import PPO
from core.meta_ai import MetaAI  # あなたの環境に合わせて

def main():
    print("✅ MetaAI PPO学習（TensorBoard対応）開始！")

    # 戦略AI群の用意（仮に全てのAIをモックで用意する場合）
    # 実際は各戦略のインポートとインスタンス化が必要です
    strategy_agents = {
        "Aurus": None,
        "Levia": None,
        "Noctus": None,
        "Prometheus": None
    }
    env = MetaAI(strategy_agents=strategy_agents)

    # TensorBoard用ログディレクトリ
    tensorboard_logdir = "./ppo_tensorboard_logs"

    # PPOのエージェント生成（TensorBoard設定込み）
    ppo_agent = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        tensorboard_log=tensorboard_logdir  # ← これがポイント
    )

    # PPO学習の実行
    ppo_agent.learn(total_timesteps=50000)

    print("✅ PPO学習（TensorBoard対応）完了！")

if __name__ == "__main__":
    main()
