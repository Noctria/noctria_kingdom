#!/usr/bin/env python3
import sys
sys.path.append('/opt/airflow')  # ✅ AirflowコンテナのPYTHONPATHを明示

import optuna
from core.meta_ai_env_with_fundamentals import TradingEnvWithFundamentals
from stable_baselines3 import PPO

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
        verbose=0
    )

    # ✅ 学習
    model.learn(total_timesteps=1000)  # テストのため短め

    # ✅ ダミーの評価指標: ここではテストとして固定の値を返す（本来は収益率などに置換）
    mean_reward = 0.0
    return mean_reward

if __name__ == "__main__":
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=10)

    print("最適ハイパーパラメータ:", study.best_params)
