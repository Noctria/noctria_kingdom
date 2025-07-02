# coding: utf-8

from core.path_config import MODELS_DIR, DATA_DIR, LOGS_DIR
from core.meta_ai_env_with_fundamentals import TradingEnvWithFundamentals
from stable_baselines3 import PPO
import os

def evaluate_metaai_model():
    model_path = MODELS_DIR / "latest" / "metaai_model_latest.zip"
    data_path = DATA_DIR / "preprocessed_usdjpy_with_fundamental.csv"

    if not model_path.exists():
        print(f"❌ モデルが見つかりません: {model_path}")
        return

    print(f"📥 モデル読込: {model_path}")
    model = PPO.load(str(model_path))

    env = TradingEnvWithFundamentals(str(data_path))
    obs = env.reset()
    total_reward = 0
    done = False

    while not done:
        action, _states = model.predict(obs)
        obs, reward, done, info = env.step(action)
        total_reward += reward

    print(f"✅ 評価完了: 累積報酬 = {total_reward}")
    result_path = LOGS_DIR / "metaai_evaluation_result.txt"
    with open(result_path, "w") as f:
        f.write(f"Total reward: {total_reward}\n")
