#!/usr/bin/env python3
# coding: utf-8

import os
import json
from core.meta_ai import MetaAI
from core.meta_ai_env_with_fundamentals import TradingEnvWithFundamentals
from stable_baselines3 import PPO

def apply_best_params_to_metaai():
    best_params_path = "/opt/airflow/logs/best_params.json"
    
    if not os.path.exists(best_params_path):
        print(f"❌ 最適化結果が見つかりません: {best_params_path}")
        return

    with open(best_params_path, "r") as f:
        best_params = json.load(f)

    print(f"📦 MetaAI: 読み込まれた最適パラメータ: {best_params}")

    # ✅ 学習環境を初期化
    data_path = "/opt/airflow/data/preprocessed_usdjpy_with_fundamental.csv"
    env = TradingEnvWithFundamentals(data_path)

    # ✅ MetaAI PPOモデル再構築・学習
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=best_params["learning_rate"],
        n_steps=best_params["n_steps"],
        gamma=best_params["gamma"],
        ent_coef=best_params["ent_coef"],
        verbose=1,
        tensorboard_log="/opt/airflow/logs/ppo_tensorboard_logs/"
    )

    print("⚙️ MetaAI: 最適化パラメータで再学習を開始します...")
    model.learn(total_timesteps=1000)

    # ✅ モデル保存（将来のロード用）
    model.save("/opt/airflow/logs/metaai_model_latest.zip")
    print("✅ MetaAI: 最適パラメータ適用後のモデルを保存しました。")

def main():
    print("👑 王Noctria: MetaAIに最適化戦略を適用し、王国の未来を切り開け！")
    apply_best_params_to_metaai()
    print("🌟 王国の進化が完了しました！MetaAIは新たな力を得ました。")

if __name__ == "__main__":
    main()
