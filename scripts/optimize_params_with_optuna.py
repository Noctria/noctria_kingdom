#!/usr/bin/env python3
# coding: utf-8

from core.path_config import *
from core.logger import setup_logger  # 🏰 ログ統治機構

import sys
import os
import optuna
import json
from datetime import datetime

from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3 import PPO
from torch.utils.tensorboard import SummaryWriter

from core.meta_ai_env_with_fundamentals import TradingEnvWithFundamentals

# ✅ 王国記録係（ログ）を召喚
logger = setup_logger("optimize_logger", LOGS_DIR / "pdca" / "optimize.log")

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
    logger.info(f"🎯 試行 {trial.number} を開始")

    learning_rate = trial.suggest_float('learning_rate', 1e-5, 1e-3, log=True)
    n_steps = trial.suggest_int('n_steps', 128, 2048)
    gamma = trial.suggest_float('gamma', 0.8, 0.9999)
    ent_coef = trial.suggest_float('ent_coef', 0.0, 0.05)

    logger.info(f"🔧 探索パラメータ: lr={learning_rate}, n_steps={n_steps}, gamma={gamma}, ent_coef={ent_coef}")

    try:
        env = TradingEnvWithFundamentals(DATA_DIR / "preprocessed_usdjpy_with_fundamental.csv")
    except Exception as e:
        logger.error(f"❌ 環境初期化失敗: {e}")
        raise

    try:
        model = PPO(
            "MlpPolicy", env,
            learning_rate=learning_rate,
            n_steps=n_steps,
            gamma=gamma,
            ent_coef=ent_coef,
            verbose=0,
            tensorboard_log=str(LOGS_DIR / "ppo_tensorboard_logs")
        )

        tb_callback = TensorBoardCallback(str(LOGS_DIR / "ppo_tensorboard_logs"), trial.number)
        model.learn(total_timesteps=1000, callback=tb_callback)

    except Exception as e:
        logger.error(f"❌ モデル学習エラー: {e}")
        raise

    try:
        mean_reward, _ = evaluate_policy(model, env, n_eval_episodes=5)
        logger.info(f"✅ 評価結果（平均報酬）: {mean_reward}")
        return mean_reward
    except Exception as e:
        logger.error(f"❌ 評価エラー: {e}")
        raise

# ✅ DAGや他スクリプトから呼べるラッパー
def optimize_main():
    study_name = "ppo_opt"
    storage = os.getenv("OPTUNA_DB_URL", "postgresql+psycopg2://airflow:airflow@postgres:5432/optuna_db")

    logger.info(f"📚 Optuna Study開始: {study_name}")
    logger.info(f"🔌 Storage: {storage}")

    try:
        study = optuna.create_study(
            direction="maximize",
            study_name=study_name,
            storage=storage,
            load_if_exists=True
        )
        study.optimize(objective, n_trials=5)
    except Exception as e:
        logger.error(f"❌ Optuna最適化エラー: {e}")
        raise

    logger.info(f"👑 最適ハイパーパラメータ: {study.best_params}")

    best_params_file = LOGS_DIR / "best_params.json"
    try:
        with open(best_params_file, "w") as f:
            json.dump(study.best_params, f, indent=2)
        logger.info(f"📁 保存完了: {best_params_file}")
    except Exception as e:
        logger.error(f"❌ best_params.json の保存失敗: {e}")
        raise

# ✅ CLI実行時（デバッグ用）
if __name__ == "__main__":
    optimize_main()
