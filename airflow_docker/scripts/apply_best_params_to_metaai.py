#!/usr/bin/env python3
# coding: utf-8

import json
from pathlib import Path

from core.meta_ai import MetaAI
from core.meta_ai_env_with_fundamentals import TradingEnvWithFundamentals
from stable_baselines3 import PPO
from core.path_config import LOGS_DIR, DATA_DIR

def apply_best_params_to_metaai():
    # ✅ パス一元管理（Noctria Kingdom v2.0構成）
    best_params_path = LOGS_DIR / "best_params.json"
    data_path = DATA_DIR / "preprocessed_usdjpy_with_fundamental.csv"
    tensorboard_log_dir = LOGS_DIR / "ppo_tensorboard_logs"
    model_save_path = LOGS_DIR / "metaai_model_latest.zip"

    if not best_params_path.exists():
        print(f"❌ 最適化結果が見つかりません: {best_params_path}")
        return

    with open(best_params_path, "r") as f:
        best_params = json.load(f)

    print(f"📦 MetaAI: 読み込まれた最適パラメータ: {best_params}")

    # ✅ 学習環境を初期化（ファンダメンタル込み）
    env = TradingEnvWithFundamentals(str(data_path))

    # ✅ MetaAI PPOモデル再構築・再学習
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=best_params["learning_rate"],
        n_steps=best_params["n_steps"],
        gamma=best_params["gamma"],
        ent_coef=best_params["ent_coef"],
        verbose=1,
        tensorboard_log=str(tensorboard_log_dir),
    )

    print("⚙️ MetaAI: 最適パラメータで再学習を開始します...")
    model.learn(total_timesteps=1000)

    # ✅ モデル保存
    model.save(str(model_save_path))
    print("✅ MetaAI: 最適パラメータ適用後のモデルを保存しました。")

def main():
    print("👑 王Noctria: MetaAIに最適化戦略を適用し、王国の未来を切り開け！")
    apply_best_params_to_metaai()
    print("🌟 王国の進化が完了しました！MetaAIは新たな力を得ました。")

if __name__ == "__main__":
    main()
