import optuna
from stable_baselines3 import PPO
from core.meta_ai_env_with_fundamentals import TradingEnvWithFundamentals

def objective(trial):
    env = TradingEnvWithFundamentals(
        data_path="/opt/airflow/data/preprocessed_usdjpy_with_fundamental.csv"
    )

    learning_rate = trial.suggest_loguniform("learning_rate", 1e-5, 1e-3)
    n_steps = trial.suggest_categorical("n_steps", [2048, 4096, 8192])
    gamma = trial.suggest_uniform("gamma", 0.9, 0.999)
    ent_coef = trial.suggest_loguniform("ent_coef", 1e-5, 1e-1)

    model = PPO("MlpPolicy", env, verbose=0,
                 learning_rate=learning_rate,
                 n_steps=n_steps,
                 gamma=gamma,
                 ent_coef=ent_coef)
    model.learn(total_timesteps=20000)

    total_reward = 0.0
    obs, _ = env.reset()
    done = False
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, done, _, _ = env.step(action)
        total_reward += reward

    return total_reward

if __name__ == "__main__":
    storage_url = "postgresql+psycopg2://airflow:airflow@postgres/airflow"
    study = optuna.create_study(
        study_name="noctria_ppo_distributed",
        storage=storage_url,
        direction="maximize",
        load_if_exists=True
    )
    study.optimize(objective, n_trials=10)
