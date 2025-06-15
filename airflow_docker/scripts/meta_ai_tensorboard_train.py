#!/usr/bin/env python3
# coding: utf-8

import sys
sys.path.append('/opt/airflow')  # 追加で core モジュールを認識させる

from stable_baselines3 import PPO
from core.meta_ai import MetaAI  # カスタム環境

def main():
    print("👑 王Noctria: Aurusよ、戦略学習の任務を開始せよ！")
    print("⚔️ Aurus: 市場データを元に、戦略を強化学習で磨きます。")
    print("🔮 Prometheus: 外部データも活用し、未来を予見して反映します。")
    print("🛡️ Noctus: 学習中のリスクに警戒を怠らぬよう監視します。")
    print("⚡ Levia: 短期利益の刈り取り準備も進めています！")

    # 🎯 各戦略エージェントの設定（例: ここでは未使用）
    strategy_agents = {
        "Aurus": None,
        "Levia": None,
        "Noctus": None,
        "Prometheus": None
    }

    # 🎯 カスタム学習環境（MetaAI）を生成
    env = MetaAI(strategy_agents=strategy_agents)

    # 🎯 TensorBoardログディレクトリ
    tensorboard_logdir = "/opt/airflow/logs/ppo_tensorboard_logs"

    # 🎯 PPOエージェントの初期化
    ppo_agent = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        tensorboard_log=tensorboard_logdir
    )

    print("⚔️ Aurus: 戦略学習サイクルを始動！")
    ppo_agent.learn(total_timesteps=50000)
    print("✅ 王Noctria: Aurus、Prometheus、Noctus、Levia…任務完了！王国の戦略がさらに磨かれた。")

if __name__ == "__main__":
    main()
