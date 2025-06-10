#!/usr/bin/env python3
# /opt/airflow/scripts/optimize_params_with_optuna.py

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))  # 🔥 /opt/airflow をパスに追加

import optuna
from core.meta_ai_env_with_fundamentals import TradingEnvWithFundamentals
from stable_baselines3 import PPO


def objective(trial):
    # ✅ ハイパーパラメータのサンプリング
    learning_rate = trial.suggest_loguniform('learning_rate', 1e-5, 1e-3)
    n_steps = trial.suggest_int('n_steps', 64, 2048, step=64)
    gamma = trial.suggest_uniform('gamma', 0.8, 0.9999)
    ent_coef = trial.suggest_uniform('ent_coef', 0.0, 0.05)

    # ✅ 環境の初期化
    env = TradingEnvWithFundamentals('/opt/airflow/data/preprocessed_usdjpy_with_fundamental.csv')

    # ✅ PPOエージェントの初期化
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=learning_rate,
        n_steps=n_steps,
        gamma=gamma,
        ent_coef=ent_coef,
        verbose=0
    )

    # ✅ 学習実行
    model.learn(total_timesteps=5000)

    # ✅ モデル評価（ここでは最終報酬を返す例）
    obs, _ = env.reset()
    total_reward = 0.0
    done = False

    while not done:
        action, _states = model.predict(obs)
        obs, reward, done, _, _ = env.step(action)
        total_reward += reward

    print(f"Trial {trial.number}: total_reward={total_reward}")
    return total_reward


if __name__ == "__main__":
    # ✅ Optunaのスタディ定義
    study = optuna.create_study(direction='maximize', study_name='noctria_hyperopt')

    # ✅ 最適化開始
    study.optimize(objective, n_trials=20)

    # ✅ 結果出力
    print("最適パラメータ:", study.best_params)
    print("最高報酬:", study.best_value)
