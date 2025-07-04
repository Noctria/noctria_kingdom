#!/usr/bin/env python3
# coding: utf-8

import os
from pathlib import Path
from stable_baselines3 import PPO
from core.meta_ai_env_with_fundamentals import TradingEnvWithFundamentals
from core.path_config import MODELS_DIR, DATA_DIR, LOGS_DIR

def evaluate_metaai_model():
    """
    最新のMetaAIモデルを評価し、累積報酬をログに出力する。
    """
    model_path = MODELS_DIR / "latest" / "metaai_model_latest.zip"
    data_path = DATA_DIR / "preprocessed_usdjpy_with_fundamental.csv"
    result_path = LOGS_DIR / "metaai_evaluation_result.txt"

    # === モデルとデータの存在確認 ===
    if not model_path.exists():
        print(f"❌ モデルが見つかりません: {model_path}")
        return

    if not data_path.exists():
        print(f"❌ データが見つかりません: {data_path}")
        return

    print(f"📥 モデル読込: {model_path}")
    model = PPO.load(str(model_path))

    # === 環境初期化と評価実行 ===
    env = TradingEnvWithFundamentals(str(data_path))
    obs = env.reset()
    total_reward = 0
    done = False

    while not done:
        action, _states = model.predict(obs)
        obs, reward, done, info = env.step(action)
        total_reward += reward

    print(f"✅ 評価完了: 累積報酬 = {total_reward:.2f}")

    # === 結果ログに保存 ===
    os.makedirs(LOGS_DIR, exist_ok=True)
    with open(result_path, "w") as f:
        f.write(f"Total reward: {total_reward:.2f}\n")
    print(f"📝 結果保存: {result_path}")
