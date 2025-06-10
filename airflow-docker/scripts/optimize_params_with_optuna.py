import sys
import os

# ✅ カレントスクリプトの親ディレクトリをパスに追加（Airflowの標準構成を想定）
sys.path.append(os.path.join(os.path.dirname(__file__), '../core'))

from core.meta_ai_env_with_fundamentals import TradingEnvWithFundamentals
from stable_baselines3 import PPO
import optuna
import numpy as np

def objective(trial):
    env = TradingEnvWithFundamentals(data_path='/opt/airflow/data/preprocessed_usdjpy_with_fundamental.csv')

    # ハイパーパラメータ探索
    learning_rate = trial.suggest_float('learning_rate', 1e-5, 1e-3, log=True)
    n_steps = trial.suggest_int('n_steps', 128, 2048)
    gamma = trial.suggest_float('gamma', 0.8, 0.9999)
    ent_coef = trial.suggest_float('ent_coef', 0.0, 0.05)

    model = PPO('MlpPolicy', env, verbose=0,
                 learning_rate=learning_rate,
                 n_steps=n_steps,
                 gamma=gamma,
                 ent_coef=ent_coef)

    # ここでは1000ステップだけ学習して報酬を返す（テスト用）
    model.learn(total_timesteps=1000)

    # 最終報酬として使う（ここではシンプルに0を返す例）
    return 0.0

if __name__ == "__main__":
    study = optuna.create_study(direction='minimize')
    study.optimize(objective, n_trials=10)

    print("最適なハイパーパラメータ:", study.best_params)
