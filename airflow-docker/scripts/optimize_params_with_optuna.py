#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('/opt/airflow/core')  # ✅ Airflow環境におけるcoreディレクトリのパスを明示的に追加

import optuna
from stable_baselines3 import PPO
from core.meta_ai_env_with_fundamentals import TradingEnvWithFundamentals


def optimize_agent(trial):
    # Hyperparameter search space
    learning_rate = trial.suggest_loguniform('learning_rate', 1e-5, 1e-3)
    n_steps = trial.suggest_int('n_steps', 128, 2048)
    gamma = trial.suggest_float('gamma', 0.8, 0.9999)
    ent_coef = trial.suggest_float('ent_coef', 0.0, 0.05)

    # 環境の初期化
    env = TradingEnvWithFundamentals(data_path='/opt/airflow/data/preprocessed_usdjpy_with_fundamental.csv')

    # エージェント初期化
    model = PPO(
        policy='MlpPolicy',
        env=env,
        verbose=0,
        learning_rate=learning_rate,
        n_steps=n_steps,
        gamma=gamma,
        ent_coef=ent_coef,
    )

    # 学習
    model.learn(total_timesteps=1000)  # ✅ 短縮版のステップ数

    # 評価
    obs, _ = env.reset()
    done = False
    cumulative_reward = 0.0
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, done, truncated, _ = env.step(action)
        cumulative_reward += reward

    return cumulative_reward


if __name__ == "__main__":
    study = optuna.create_study(direction='maximize')
    study.optimize(optimize_agent, n_trials=10)

    print("最適化結果:")
    print(study.best_params)
    print("最適報酬:", study.best_value)
