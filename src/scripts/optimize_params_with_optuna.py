"""
直インスタンス方式対応版:
- env_id が "module.path:ClassName" ならクラスを import して **直接インスタンス化**
- それ以外（例: "CartPole-v1"）は従来どおり gym.make()
- Airflow context から params / conf を安全に吸い上げ
- 戻り値は {study_name, best_value, best_params, n_trials, datetime_utc, worker_tag}
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional, Callable
import os
from datetime import datetime
from importlib import import_module

# --------- 軽量ログ ---------
def _log(msg: str) -> None:
    print(f"[{datetime.utcnow():%Y-%m-%d %H:%M:%S} UTC] {msg}", flush=True)

# --------- 遅延import（重い依存は遅延で） ---------
def _lazy_imports():
    import numpy as np
    try:
        import gymnasium as gym
    except Exception:
        import gymnasium as gym  # gymではなくgymnasiumに統一
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv
    from stable_baselines3.common.evaluation import evaluate_policy
    import optuna
    return dict(np=np, gym=gym, PPO=PPO, DummyVecEnv=DummyVecEnv,
                evaluate_policy=evaluate_policy, optuna=optuna)

# --------- 直インスタンス解決 ---------
def _resolve_env_factory(env_target: str, env_kwargs: Optional[dict] = None) -> Optional[Callable[[], Any]]:
    """
    env_target が 'module.path:ClassName' 形式なら、そのクラスを import して
    kwargsを渡してインスタンス化する factory を返す。違うなら None。
    """
    if ":" not in env_target:
        return None
    module_path, class_name = env_target.split(":", 1)
    cls = getattr(import_module(module_path), class_name)

    def _factory():
        kwargs = env_kwargs or {}
        return cls(**kwargs)

    return _factory

# --------- 設定 ---------
@dataclass
class OptunaConfig:
    study_name: str = "noctria_rl_ppo"
    storage_url: Optional[str] = None   # 省略時はENV OPTUNA_STORAGE
    sampler: str = "tpe"                # tpe|random|cmaes
    pruner: str = "median"              # median|none
    direction: str = "maximize"         # maximize|minimize
    n_trials: int = 20
    timeout_sec: Optional[int] = None

    # 環境
    env_id: str = "CartPole-v1"         # 例: "src.envs.your_custom_trading_env:YourCustomTradingEnv"
    env_kwargs: Optional[dict] = None
    seed: Optional[int] = None

    # PPO/学習
    max_train_steps: int = 100_000
    n_eval_episodes: int = 5
    allow_prune_after: int = 2_000
    tb_logdir: Optional[str] = None

# --------- 目的関数 ---------
def make_objective(cfg: OptunaConfig):
    mods = _lazy_imports()
    np = mods["np"]
    gym = mods["gym"]
    PPO = mods["PPO"]
    DummyVecEnv = mods["DummyVecEnv"]
    evaluate_policy = mods["evaluate_policy"]
    optuna_mod = mods["optuna"]

    # env factory（直インスタンス or gym.make）
    def _make_env():
        factory = _resolve_env_factory(cfg.env_id, cfg.env_kwargs)
        if factory:
            return factory()
        return gym.make(cfg.env_id)

    def objective(trial: "optuna.trial.Trial") -> float:
        # Hyperparameter Search Space
        learning_rate = trial.suggest_float("learning_rate", 1e-5, 1e-3, log=True)
        n_steps = trial.suggest_categorical("n_steps", [128, 384, 768, 896, 1536, 1792, 2048])
        gamma = trial.suggest_float("gamma", 0.90, 0.99, step=0.001)
        ent_coef = trial.suggest_float("ent_coef", 5e-4, 2e-2, step=5e-4)
        clip_range = trial.suggest_float("clip_range", 0.12, 0.4, step=0.02)
        gae_lambda = trial.suggest_float("gae_lambda", 0.80, 0.97, step=0.01)
        vf_coef = trial.suggest_float("vf_coef", 0.2, 1.0, step=0.05)
        batch_size = trial.suggest_categorical("batch_size", [64, 128, 256])

        # VecEnv 準備
        try:
            def _env_fn():
                env = _make_env()
                if cfg.seed is not None:
                    try:
                        env.reset(seed=cfg.seed)
                    except TypeError:
                        pass
                return env

            vec_env = DummyVecEnv([_env_fn])
        except Exception as e:
            _log(f"❌ 環境作成に失敗: {e}")
            raise

        # PPO モデル
        try:
            model = PPO(
                "MlpPolicy",
                vec_env,
                learning_rate=learning_rate,
                n_steps=n_steps,
                gamma=gamma,
                ent_coef=ent_coef,
                clip_range=clip_range,
                gae_lambda=gae_lambda,
                vf_coef=vf_coef,
                batch_size=batch_size,
                verbose=0,
                tensorboard_log=cfg.tb_logdir,
                seed=cfg.seed,
            )
        except Exception as e:
            _log(f"❌ モデル初期化失敗: {e}")
            vec_env.close()
            raise

        # 学習（途中打ち切りのための簡易コールバック）
        train_steps = int(cfg.max_train_steps)
        try:
            model.learn(total_timesteps=train_steps, progress_bar=False, tb_log_name=f"trial_{trial.number}")
        except Exception as e:
            _log(f"⚠️ 学習中に例外: {e}")
            # 失敗扱い（OptunaがFailにする）
            vec_env.close()
            raise

        # 評価
        try:
            mean_reward, _ = evaluate_policy(model, vec_env, n_eval_episodes=int(cfg.n_eval_episodes),
                                             deterministic=True, warn=False)
        except Exception as e:
            _log(f"⚠️ 評価中に例外: {e}")
            vec_env.close()
            raise
        finally:
            vec_env.close()

        # maximize 前提（minimizeなら符号反転も可）
        value = float(mean_reward)
        return value

    return objective

# --------- 実行ロジック ---------
def run(cfg: OptunaConfig) -> Dict[str, Any]:
    mods = _lazy_imports()
    optuna_mod = mods["optuna"]

    storage = cfg.storage_url or os.getenv("OPTUNA_STORAGE") or None
    _log(f"🎯 Study: {cfg.study_name} ({cfg.direction}), storage={storage or 'None'}, worker={os.getenv('HOSTNAME','worker')}")

    # Sampler
    sampler: "optuna.samplers.BaseSampler"
    if cfg.sampler.lower() == "tpe":
        sampler = optuna_mod.samplers.TPESampler(seed=cfg.seed)
    elif cfg.sampler.lower() == "cmaes":
        sampler = optuna_mod.samplers.CmaEsSampler(seed=cfg.seed)
    else:
        sampler = optuna_mod.samplers.RandomSampler(seed=cfg.seed)

    # Pruner
    pruner: Optional["optuna.pruners.BasePruner"]
    if cfg.pruner.lower() == "median":
        pruner = optuna_mod.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=cfg.allow_prune_after)
    else:
        pruner = None

    # Study 作成/取得
    study = optuna_mod.create_study(
        study_name=cfg.study_name,
        storage=storage,
        load_if_exists=True,
        direction=cfg.direction,
        sampler=sampler,
        pruner=pruner,
    )

    objective = make_objective(cfg)
    study.optimize(objective, n_trials=int(cfg.n_trials), timeout=cfg.timeout_sec)

    best_value = float(study.best_value)
    best_params = dict(study.best_trial.params)
    result = {
        "study_name": cfg.study_name,
        "best_value": best_value,
        "best_params": best_params,
        "n_trials": len(study.trials),
        "datetime_utc": datetime.utcnow().isoformat(),
        "worker_tag": f"worker-{os.getenv('HOSTNAME','worker')}",
    }
    _log(f"✅ 最適化完了: best_value={best_value}, best_params={best_params}")
    return result

# --------- Airflow / CLI エントリ ---------
def optimize_main(*args, **kwargs) -> Dict[str, Any]:
    """
    Airflow の PythonOperator から context を受け取り、params/conf を束ねる。
    """
    # Airflow context 経由で params / conf を吸い上げ
    params = {}
    if "dag_run" in kwargs and getattr(kwargs["dag_run"], "conf", None):
        params.update(kwargs["dag_run"].conf)
    if "params" in kwargs and kwargs["params"]:
        params.update(kwargs["params"])

    # マージ（params側が優先）
    cfg = OptunaConfig(
        study_name=str(params.get("study_name", "noctria_rl_ppo")),
        storage_url=params.get("storage_url", None),
        sampler=str(params.get("sampler", "tpe")),
        pruner=str(params.get("pruner", "median")),
        direction=str(params.get("direction", "maximize")),
        n_trials=int(params.get("n_trials", 20)),
        timeout_sec=int(params.get("timeout_sec")) if params.get("timeout_sec") is not None else None,
        env_id=str(params.get("env_id", "CartPole-v1")),
        env_kwargs=params.get("env_kwargs"),
        seed=int(params.get("seed")) if params.get("seed") is not None else None,
        max_train_steps=int(params.get("max_train_steps", 100_000)),
        n_eval_episodes=int(params.get("n_eval_episodes", 5)),
        allow_prune_after=int(params.get("allow_prune_after", 2_000)),
        tb_logdir=params.get("tb_logdir"),
    )
    return run(cfg)

# CLI 実行も可（任意）
if __name__ == "__main__":
    # 簡易デモ: CartPole
    res = optimize_main(params={
        "study_name": "demo_cartpole",
        "env_id": "CartPole-v1",
        "n_trials": 2,
        "max_train_steps": 20_000,
        "n_eval_episodes": 2,
        "timeout_sec": 120,
    })
    print(res)
