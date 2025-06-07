#!/usr/bin/env python3
# coding: utf-8

import gym
import numpy as np
from stable_baselines3 import PPO
from core.meta_ai import MetaAI  # 環境に合わせてパスを調整

def main():
    print("✅ MetaAI PPO学習（TensorBoard対応・logsディレクトリ）開始！")

    # 各戦略AIのモック（実際は本物の戦略クラスをインポート・インスタンス化）
    strategy_agents = {
        "Aurus": None,
        "Levia": None,
        "Noctus": None,
        "Prometheus": None
    }

    # MetaAI環境の生成
    env = MetaAI(strategy_agents=strategy_agents)

    # logsディレクトリにTensorBoardログを保存
    tensorboard_logdir = "logs/ppo_tensorboard_logs"

    # PPOエージェントの生成（学習率を変更）
    ppo_agent = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        tensorboard_log=tensorboard_logdir,
        learning_rate=0.0001  # 学習率を0.0001に変更
    )

    # PPO学習の実行
    ppo_agent.learn(total_timesteps=50000)

    print("✅ PPO学習（TensorBoard対応・logsディレクトリ）完了！")

if __name__ == "__main__":
    main()
