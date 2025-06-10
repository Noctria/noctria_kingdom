import optuna
from stable_baselines3 import PPO
from core.meta_ai_env_with_fundamentals import TradingEnvWithFundamentals

def optimize(trial):
    # 各 Trial 専用の TensorBoard ログディレクトリ
    log_dir = f"/opt/airflow/logs/ppo_tensorboard_logs/trial_{trial.number}"
    print(f"TensorBoard ログディレクトリ: {log_dir}")

    # 環境のセットアップ
    env = TradingEnvWithFundamentals("/opt/airflow/data/preprocessed_usdjpy_with_fundamental.csv")

    # Optuna のパラメータ探索
    learning_rate = trial.suggest_float('learning_rate', 1e-5, 1e-3, log=True)
    n_steps = trial.suggest_int('n_steps', 128, 2048, step=128)
    gamma = trial.suggest_float('gamma', 0.8, 0.9999)
    ent_coef = trial.suggest_float('ent_coef', 0.0, 0.05)

    # PPO モデルの作成（Trial専用の TensorBoard ログディレクトリ指定）
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        tensorboard_log=log_dir,
        learning_rate=learning_rate,
        n_steps=n_steps,
        gamma=gamma,
        ent_coef=ent_coef
    )

    # 学習
    model.learn(total_timesteps=1000)

    # 最終報酬（例として環境のカスタム評価関数を呼ぶ想定）
    mean_reward = 0.0  # 例: 直近の平均リワードを保存するなら実装する
    return mean_reward

if __name__ == "__main__":
    study = optuna.create_study(direction='maximize', study_name='noctria-ppo-study')
    study.optimize(optimize, n_trials=10, n_jobs=2)  # n_jobs=2 で並列試行
