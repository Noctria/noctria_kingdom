#!/usr/bin/env python3
# coding: utf-8

import sys
sys.path.append('/opt/airflow')  # Airflow内で core モジュールが見えるようにする！

import gym
import numpy as np
from stable_baselines3 import PPO
from core.meta_ai import MetaAI  # core モジュール

def main():
    print("👑 王Noctria: Aurusよ、戦略学習の任務を開始せよ！")
    print("⚔️ Aurus: 市場データを元に、戦略を強化学習で磨きます。")
    print("🔮 Prometheus: 外部データも活用し、未来を予見して反映します。")
    print("🛡️ Noctus: 学習中のリスクに警戒を怠らぬよう監視します。")
    print("⚡ Levia: 短期利益の刈り取り準備も進めています！")

    # 各戦略AIのモック（本番では本物クラスをインポートして置き換える）
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

    # PPOエージェントの生成（TensorBoard設定込み）
    ppo_agent = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        tensorboard_log=tensorboard_logdir
    )

    print("⚔️ Aurus: 戦略学習サイクルを始動！王国の勝利を目指します。")
    ppo_agent.learn(total_timesteps=50000)
    print("✅ 王Noctria: Aurus、Prometheus、Noctus、Levia…任務完了！王国の戦略がさらに磨かれた。")

if __name__ == "__main__":
    main()
