#!/usr/bin/env python3
# coding: utf-8

import sys
import os
import optuna
import json
from datetime import datetime

# ✅ Noctria KingdomプロジェクトのルートをPythonパスに追加（Docker内パス）
sys.path.append('/noctria_kingdom/airflow_docker')

# ✅ Optuna + TensorBoard用
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.evaluation import evaluate_policy
from torch.utils.tensorboard import SummaryWriter
from stable_baselines3 import PPO

# ✅ Noctria王国の自作強化学習環境
from core.meta_ai_env_with_fundamentals import TradingEnvWithFundamentals

# ✅ TensorBoard書き込み用Callback定義
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

# ✅ Optunaの目的関数
def objective(trial):
    # 探索するハイパーパラメータ
    learning_rate = trial.suggest_float('learning_rate', 1e-5, 1e-3, log=True)
    n_steps = trial.suggest_int('n_steps', 128, 2048)
    gamma = trial.suggest_float('gamma', 0.8, 0.9999)
    ent_coef = trial.suggest_float('ent_coef', 0.0, 0.05)

    # 自作環境の初期化
    env = TradingEnvWithFundamentals('/noctria_kingdom/airflow_docker/data/preprocessed_usdjpy_with_fundamental.csv')

    # PPOモデルの構築
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=learning_rate,
        n_steps=n_steps,
        gamma=gamma,
        ent_coef=ent_coef,
        verbose=0,
        tensorboard_log="/noctria_kingdom/airflow_docker/logs/ppo_tensorboard_logs/"
    )

    # TensorBoard用Callback
    tb_callback = TensorBoardCallback("/noctria_kingdom/airflow_docker/logs/ppo_tensorboard_logs", trial.number)

    # モデル学習
    model.learn(total_timesteps=1000, callback=tb_callback)

    # モデル評価（平均報酬）
    mean_reward, _ = evaluate_policy(model, env, n_eval_episodes=5)
    return mean_reward

# ✅ メイン処理
if __name__ == "__main__":
    study_name = "ppo_opt"

    # PostgreSQL Optuna DBの接続URL
    storage = os.getenv(
        "OPTUNA_DB_URL",
        "postgresql+psycopg2://airflow:airflow@postgres:5432/optuna_db"
    )

    # Study作成（既存があれば再利用）
    study = optuna.create_study(
        direction="maximize",
        study_name=study_name,
        storage=storage,
        load_if_exists=True
    )

    # 最適化実行（試行回数は任意に調整）
    study.optimize(objective, n_trials=5)

    # 最適パラメータをログ出力＆保存
    print("✅ 最適ハイパーパラメータ:", study.best_params)

    best_params_file = "/noctria_kingdom/airflow_docker/logs/best_params.json"
    with open(best_params_file, "w") as f:
        json.dump(study.best_params, f, indent=2)
