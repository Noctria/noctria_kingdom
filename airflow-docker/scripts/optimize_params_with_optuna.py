#!/usr/bin/env python3
import sys
import os
import optuna
from datetime import datetime

# AirflowコンテナのPYTHONPATHを明示
sys.path.append('/opt/airflow')

# TensorBoard用
from stable_baselines3.common.callbacks import BaseCallback
from torch.utils.tensorboard import SummaryWriter

# 環境クラス・モデル
from core.meta_ai_env_with_fundamentals import TradingEnvWithFundamentals
from stable_baselines3 import PPO

# ✅ TensorBoard記録用コールバック
class TrialTensorBoardCallback(BaseCallback):
    def __init__(self, base_log_dir, trial_number, verbose=0):
        super().__init__(verbose)
        self.log_dir = os.path.join(base_log_dir, f"trial_{trial_number}")
        os.makedirs(self.log_dir, exist_ok=True)
        self.writer = SummaryWriter(log_dir=self.log_dir)

    def _on_step(self) -> bool:
        # 例: ダミーで報酬0.0を記録
        self.writer.add_scalar("charts/reward", 0.0, self.num_timesteps)
        return True

    def _on_training_end(self) -> None:
        self.writer.close()

# ✅ Optunaの目的関数
def objective(trial):
    # Optunaで試すハイパーパラメータ
    learning_rate = trial.suggest_float('learning_rate', 1e-5, 1e-3, log=True)
    n_steps = trial.suggest_int('n_steps', 128, 2048)
    gamma = trial.suggest_float('gamma', 0.8, 0.9999)
    ent_coef = trial.suggest_float('ent_coef', 0.0, 0.05)

    # 環境初期化
    env = TradingEnvWithFundamentals('/opt/airflow/data/preprocessed_usdjpy_with_fundamental.csv')

    # モデル初期化（TensorBoardログdirも指定）
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=learning_rate,
        n_steps=n_steps,
        gamma=gamma,
        ent_coef=ent_coef,
        verbose=0,
        tensorboard_log="/opt/airflow/logs/ppo_tensorboard_logs/"
    )

    # TensorBoardコールバック
    tb_callback = TrialTensorBoardCallback("/opt/airflow/logs/ppo_tensorboard_logs", trial.number)

    # 学習
    model.learn(total_timesteps=1000, callback=tb_callback)

    # ここではダミーで固定値（実際は mean_reward などを返す）
    mean_reward = 0.0
    return mean_reward

if __name__ == "__main__":
    # Optunaのスタディ設定（Postgres DB例）
    study_name = "ppo_hyperparam_optimization"
    storage = "postgresql+psycopg2://airflow:airflow@postgres/optuna_db"

    study = optuna.create_study(
        direction="maximize",
        study_name=study_name,
        storage=storage,
        load_if_exists=True
    )

    study.optimize(objective, n_trials=10)
    print("最適ハイパーパラメータ:", study.best_params)
