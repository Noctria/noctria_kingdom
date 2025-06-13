#!/usr/bin/env python3
# coding: utf-8

import sys
import os
import optuna
from datetime import datetime

# ✅ Airflow環境のパスを追加（コンテナ内絶対パス）
sys.path.append('/opt/airflow')

# ✅ Optuna + TensorBoard ログ
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.evaluation import evaluate_policy
from torch.utils.tensorboard import SummaryWriter
from stable_baselines3 import PPO

# ✅ 独自のトレード環境
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
    # ハイパーパラメータの探索空間
    learning_rate = trial.suggest_float('learning_rate', 1e-5, 1e-3, log=True)
    n_steps = trial.suggest_int('n_steps', 128, 2048)
    gamma = trial.suggest_float('gamma', 0.8, 0.9999)
    ent_coef = trial.suggest_float('ent_coef', 0.0, 0.05)

    # 環境初期化
    env = TradingEnvWithFundamentals('/opt/airflow/data/preprocessed_usdjpy_with_fundamental.csv')

    # モデル初期化
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

    # TensorBoard出力先
    tb_callback = TensorBoardCallback("/opt/airflow/logs/ppo_tensorboard_logs", trial.number)

    # モデル学習
    model.learn(total_timesteps=1000, callback=tb_callback)

    # モデル評価（報酬平均）
    mean_reward, _ = evaluate_policy(model, env, n_eval_episodes=5)
    return mean_reward

if __name__ == "__main__":
    # ✅ study_nameは短く（PostgreSQLのカラム長制限対応）
    study_name = "ppo_opt"
    storage = os.getenv("OPTUNA_DB_URL", "postgresql+psycopg2://airflow:airflow@postgres/optuna_db")

    study = optuna.create_study(
        direction="maximize",
        study_name=study_name,
        storage=storage,
        load_if_exists=True
    )

    study.optimize(objective, n_trials=5)

    print("✅ 最適ハイパーパラメータ:", study.best_params)

    # オプションで保存
    best_params_file = "/opt/airflow/logs/best_params.json"
    with open(best_params_file, "w") as f:
        json.dump(study.best_params, f, indent=2)
