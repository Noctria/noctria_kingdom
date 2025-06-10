#!/usr/bin/env python3
import sys
import os
import optuna
from datetime import datetime

# ✅ AirflowコンテナのPYTHONPATHを明示
sys.path.append('/opt/airflow')

# ✅ TensorBoardのロガー設定
from stable_baselines3.common.callbacks import BaseCallback
from torch.utils.tensorboard import SummaryWriter

from core.meta_ai_env_with_fundamentals import TradingEnvWithFundamentals
from stable_baselines3 import PPO

# ✅ TensorBoardCallbackクラス（報酬取得ロジック追加済み）
class TensorBoardCallback(BaseCallback):
    def __init__(self, log_dir, trial_number, verbose=0):
        super().__init__(verbose)
        self.writer = SummaryWriter(log_dir=os.path.join(log_dir, f"trial_{trial_number}"))
        self.episode_rewards = []

    def _on_step(self) -> bool:
        # ✅ 直近の報酬を取得して記録
        rewards = self.locals.get('rewards', [0])
        if rewards:
            last_reward = rewards[-1]
            self.writer.add_scalar("charts/step_reward", last_reward, self.num_timesteps)
            self.episode_rewards.append(last_reward)
        return True

    def _on_rollout_end(self) -> None:
        # ✅ 1エピソード分の合計報酬を記録
        if self.episode_rewards:
            episode_return = sum(self.episode_rewards)
            self.writer.add_scalar("charts/episode_return", episode_return, self.num_timesteps)
            self.episode_rewards.clear()

    def _on_training_end(self) -> None:
        self.writer.close()

# ✅ Optunaの目的関数
def objective(trial):
    # 🎯 Optunaで試すハイパーパラメータ
    learning_rate = trial.suggest_float('learning_rate', 1e-5, 1e-3, log=True)
    n_steps = trial.suggest_int('n_steps', 128, 2048)
    gamma = trial.suggest_float('gamma', 0.8, 0.9999)
    ent_coef = trial.suggest_float('ent_coef', 0.0, 0.05)

    # ✅ 環境の初期化
    env = TradingEnvWithFundamentals('/opt/airflow/data/preprocessed_usdjpy_with_fundamental.csv')

    # ✅ モデルの初期化
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

    # ✅ コールバック（TensorBoardにログ出力）
    tb_callback = TensorBoardCallback("/opt/airflow/logs/ppo_tensorboard_logs", trial.number)

    # ✅ 学習
    model.learn(total_timesteps=1000, callback=tb_callback)  # ← ステップ数はお好みで調整可

    # ✅ 評価指標: ここでは固定のダミー値を返す（必要に応じて更新）
    mean_reward = 0.0
    return mean_reward

if __name__ == "__main__":
    # ✅ Optunaのスタディ名・PostgreSQLストレージ指定
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
