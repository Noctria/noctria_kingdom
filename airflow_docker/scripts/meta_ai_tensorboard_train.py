#!/usr/bin/env python3
# coding: utf-8

import os
import sys
sys.path.append('/opt/airflow')  # Docker/Airflow用のパス

from stable_baselines3 import PPO
from core.meta_ai import MetaAI  # カスタム環境

def main():
    print("👑 王Noctria: Aurusよ、戦略学習の任務を開始せよ！")
    print("⚔️ Aurus: 市場データを元に、戦略を強化学習で磨きます。")
    print("🔮 Prometheus: 外部データも活用し、未来を予見して反映します。")
    print("🛡️ Noctus: 学習中のリスクに警戒を怠らぬよう監視します。")
    print("⚡ Levia: 短期利益の刈り取り準備も進めています！")

    # 🎯 各戦略エージェントの設定（仮のNone）
    strategy_agents = {
        "Aurus": None,
        "Levia": None,
        "Noctus": None,
        "Prometheus": None
    }

    # ✅ データパスの柔軟化（環境変数 or デフォルト）
    base_data_path = os.environ.get("NOCTRIA_DATA_DIR", "/opt/airflow/data")
    full_data_path = os.path.join(base_data_path, "preprocessed_usdjpy_with_fundamental.csv")

    # 🎯 カスタム学習環境（MetaAI）を生成
    env = MetaAI(strategy_agents=strategy_agents, data_path=full_data_path)

    # 🎯 TensorBoardログディレクトリ
    tensorboard_logdir = os.environ.get("NOCTRIA_TB_LOG", "/opt/airflow/logs/ppo_tensorboard_logs")
    os.makedirs(tensorboard_logdir, exist_ok=True)

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
