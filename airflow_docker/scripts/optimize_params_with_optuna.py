#!/usr/bin/env python3
# coding: utf-8

import sys
import os
import optuna
import json
from datetime import datetime

# ✅ Airflowパス追加（Docker内部用）
sys.path.append('/noctria_kingdom/airflow_docker')

# ✅ Optuna + TensorBoard
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.evaluation import evaluate_policy
from torch.utils.tensorboard import SummaryWriter
from stable_baselines3 import PPO

# ✅ Noctria王国の自作環境
from core.meta_ai_env_with_fundamentals import TradingEnvWithFundamentals

# ✅ TensorBoard Callback
class TensorBoardCallback(BaseCallback):
    def __init__(self, log_dir, trial_number, verbose=0):
        super().__init__(verbose)
        self.writer = SummaryWriter(log_dir=os.path.join(log_dir, f"trial_{trial_number}"))
        self.episode_rewards = []

    def _on_step(self) -> bool:
        rewards = self.locals.get('rewards', [0])
        if rewards:
            last_reward = rewards[-1]
            self.writer.add_scalar("charts/step_reward", last_reward, self.num_timesteps)
            self.episode_rewards.append(last_reward)
        return True

    def _on_rollout_end(self) -> None:
        if self.episode_rewards:
            episode_return = sum(self.episode_rewards)
            self.writer.add_scalar("charts/episode_return", episode_return, self.num_timesteps)
            self.episode_rewards.clear()

    def _on_training_end(self) -> None:
        self.writer.close()

# ✅ Optuna 目的関数
def objective(trial):
    print(f"🎯 試行 {trial.number} を開始")

    # ハイパーパラメータ探索空間
    learning_rate = trial.suggest_float('learning_rate', 1e-5, 1e-3, log=True)
    n_steps = trial.suggest_int('n_steps', 128, 2048)
    gamma = trial.suggest_float('gamma', 0.8, 0.9999)
    ent_coef = trial.suggest_float('ent_coef', 0.0, 0.05)

    print(f"🔧 パラメータ: lr={learning_rate}, n_steps={n_steps}, gamma={gamma}, ent_coef={ent_coef}")

    # 環境の初期化
    try:
        env = TradingEnvWithFundamentals('/noctria_kingdom/airflow_docker/data/preprocessed_usdjpy_with_fundamental.csv')
    except Exception as e:
        print(f"❌ 環境初期化失敗: {e}")
        raise

    try:
        model = PPO(
            "MlpPolicy", env,
            learning_rate=learning_rate,
            n_steps=n_steps,
            gamma=gamma,
            ent_coef=ent_coef,
            verbose=1,
            tensorboard_log="/noctria_kingdom/airflow_docker/logs/ppo_tensorboard_logs/"
        )

        tb_callback = TensorBoardCallback("/noctria_kingdom/airflow_docker/logs/ppo_tensorboard_logs", trial.number)
        model.learn(total_timesteps=1000, callback=tb_callback)

    except Exception as e:
        print(f"❌ モデル学習エラー: {e}")
        raise

    try:
        mean_reward, _ = evaluate_policy(model, env, n_eval_episodes=5)
        print(f"✅ 評価結果（平均報酬）: {mean_reward}")
        return mean_reward
    except Exception as e:
        print(f"❌ 評価エラー: {e}")
        raise

# ✅ メイン処理
if __name__ == "__main__":
    study_name = "ppo_opt"
    storage = os.getenv("OPTUNA_DB_URL", "postgresql+psycopg2://airflow:airflow@postgres:5432/optuna_db")

    print(f"📚 Optuna Study開始: {study_name}")
    print(f"🔌 Storage: {storage}")

    try:
        study = optuna.create_study(
            direction="maximize",
            study_name=study_name,
            storage=storage,
            load_if_exists=True
        )
        study.optimize(objective, n_trials=5)
    except Exception as e:
        print(f"❌ Optuna最適化エラー: {e}")
        raise

    print("✅ 最適ハイパーパラメータ:", study.best_params)

    best_params_file = "/noctria_kingdom/airflow_docker/logs/best_params.json"
    try:
        with open(best_params_file, "w") as f:
            json.dump(study.best_params, f, indent=2)
        print(f"📁 保存完了: {best_params_file}")
    except Exception as e:
        print(f"❌ best_params.json の保存失敗: {e}")
        raise
