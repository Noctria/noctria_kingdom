#!/usr/bin/env python3
# coding: utf-8
"""
Noctria Kingdom - Optuna最適化 実行スクリプト（Airflow/CLI両対応・遅延インポート版）

特徴:
- 0.0 固定スコア対策（評価ラッパ、NaN/Inf 防御、早期終了例外の健全化）
- サンプラー/プルーナー適正化（TPESampler + MedianPruner 既定）
- エピソード複数回の安定評価
- 分散実行（RDBストレージ）: PostgreSQL想定
- 重い依存は遅延インポートでDagBagタイムアウト回避
- Airflowから呼べる optimize_main() を提供（XComで返却）
"""

from __future__ import annotations
import os
import sys
import math
import json
import random
import argparse
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path

# --- プロジェクトルート解決（/src 絶対インポート統一） ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # .../noctria_kingdom
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

def _log(msg: str) -> None:
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts} UTC] {msg}", flush=True)

@dataclass
class OptunaConfig:
    study_name: str
    storage_url: Optional[str]
    n_trials: int
    timeout_sec: Optional[int]
    n_startup_trials: int
    n_eval_episodes: int
    max_train_steps: int
    sampler: str
    pruner: str
    seed: int
    tb_logdir: Optional[str]
    env_id: str
    reward_clip: Optional[float]
    minimize: bool
    allow_prune_after: int
    worker_tag: str

def build_config(args: argparse.Namespace) -> OptunaConfig:
    def env_or_arg(key: str, default: Any):
        return os.getenv(key, getattr(args, key, default)) or default

    storage = env_or_arg("OPTUNA_STORAGE", args.storage_url)
    if isinstance(storage, str) and storage.strip() == "":
        storage = None

    return OptunaConfig(
        study_name=env_or_arg("STUDY_NAME", args.study_name),
        storage_url=storage,
        n_trials=int(env_or_arg("N_TRIALS", args.n_trials)),
        timeout_sec=int(env_or_arg("TIMEOUT_SEC", args.timeout_sec)) if env_or_arg("TIMEOUT_SEC", args.timeout_sec) else None,
        n_startup_trials=int(env_or_arg("N_STARTUP_TRIALS", args.n_startup_trials)),
        n_eval_episodes=int(env_or_arg("N_EVAL_EPISODES", args.n_eval_episodes)),
        max_train_steps=int(env_or_arg("MAX_TRAIN_STEPS", args.max_train_steps)),
        sampler=str(env_or_arg("SAMPLER", args.sampler)).lower(),
        pruner=str(env_or_arg("PRUNER", args.pruner)).lower(),
        seed=int(env_or_arg("SEED", args.seed)),
        tb_logdir=env_or_arg("TB_LOGDIR", args.tb_logdir),
        env_id=str(env_or_arg("ENV_ID", args.env_id)),
        reward_clip=float(env_or_arg("REWARD_CLIP", args.reward_clip)) if env_or_arg("REWARD_CLIP", args.reward_clip) else None,
        minimize=bool(str(env_or_arg("MINIMIZE", args.minimize)).lower() in ("1","true","yes")),
        allow_prune_after=int(env_or_arg("ALLOW_PRUNE_AFTER", args.allow_prune_after)),
        worker_tag=str(env_or_arg("WORKER_TAG", args.worker_tag)),
    )

# --- 遅延インポート（重い依存はここで） ---
def _lazy_imports():
    import numpy as np  # noqa
    import optuna  # noqa
    from optuna import Trial  # noqa
    from optuna.samplers import TPESampler, RandomSampler  # noqa
    from optuna.pruners import MedianPruner, SuccessiveHalvingPruner, NopPruner  # noqa

    try:
        from stable_baselines3 import PPO
        from stable_baselines3.common.vec_env import DummyVecEnv
        from stable_baselines3.common.evaluation import evaluate_policy
    except Exception as e:
        _log(f"⚠️ SB3 importに失敗: {e}. 'pip install stable-baselines3' を実行してください。")
        raise

    try:
        import gymnasium as gym
    except Exception:
        import gym
        gym.logger.set_level(40)

    return {
        "np": __import__("numpy"),
        "optuna": __import__("optuna"),
        "TPESampler": __import__("optuna.samplers", fromlist=["TPESampler"]).TPESampler,
        "RandomSampler": __import__("optuna.samplers", fromlist=["RandomSampler"]).RandomSampler,
        "MedianPruner": __import__("optuna.pruners", fromlist=["MedianPruner"]).MedianPruner,
        "SuccessiveHalvingPruner": __import__("optuna.pruners", fromlist=["SuccessiveHalvingPruner"]).SuccessiveHalvingPruner,
        "NopPruner": __import__("optuna.pruners", fromlist=["NopPruner"]).NopPruner,
        "PPO": __import__("stable_baselines3", fromlist=["PPO"]).PPO,
        "DummyVecEnv": __import__("stable_baselines3.common.vec_env", fromlist=["DummyVecEnv"]).DummyVecEnv,
        "evaluate_policy": __import__("stable_baselines3.common.evaluation", fromlist=["evaluate_policy"]).evaluate_policy,
        "gym": __import__("gymnasium") if "gymnasium" in sys.modules else __import__("gym"),
    }

def _make_sampler_pruner(cfg: OptunaConfig, _optuna) -> Tuple[Any, Any]:
    Samplers = {
        "tpe": __import__("optuna.samplers", fromlist=["TPESampler"]).TPESampler,
        "random": __import__("optuna.samplers", fromlist=["RandomSampler"]).RandomSampler,
    }
    Pruners = {
        "median": __import__("optuna.pruners", fromlist=["MedianPruner"]).MedianPruner,
        "sha": __import__("optuna.pruners", fromlist=["SuccessiveHalvingPruner"]).SuccessiveHalvingPruner,
        "none": __import__("optuna.pruners", fromlist=["NopPruner"]).NopPruner,
    }
    sampler_cls = Samplers.get(cfg.sampler, Samplers["tpe"])
    pruner_cls = Pruners.get(cfg.pruner, Pruners["median"])

    sampler = sampler_cls(seed=cfg.seed)
    if pruner_cls.__name__ == "MedianPruner":
        pruner = pruner_cls(n_startup_trials=cfg.n_startup_trials, n_warmup_steps=0)
    elif pruner_cls.__name__ == "SuccessiveHalvingPruner":
        pruner = pruner_cls(min_resource=cfg.allow_prune_after, reduction_factor=3)
    else:
        pruner = pruner_cls()
    return sampler, pruner

def _safe_mean(xs):
    xs = [x for x in xs if x is not None and not math.isnan(x) and math.isfinite(x)]
    return float(sum(xs) / len(xs)) if xs else 0.0

def make_objective(cfg: OptunaConfig):
    mods = _lazy_imports()
    np = mods["np"]
    gym = mods["gym"]
    PPO = mods["PPO"]
    DummyVecEnv = mods["DummyVecEnv"]
    evaluate_policy = mods["evaluate_policy"]
    optuna_mod = mods["optuna"]

    random.seed(cfg.seed)
    np.random.seed(cfg.seed)
    try:
        import torch
        torch.manual_seed(cfg.seed)
    except Exception:
        pass

    def objective(trial: "optuna.trial.Trial") -> float:
        learning_rate = trial.suggest_float("learning_rate", 1e-5, 5e-3, log=True)
        n_steps = trial.suggest_int("n_steps", 128, 2048, step=128)
        gamma = trial.suggest_float("gamma", 0.90, 0.999, step=0.001)
        ent_coef = trial.suggest_float("ent_coef", 0.0, 0.02, step=0.0005)
        clip_range = trial.suggest_float("clip_range", 0.1, 0.4, step=0.02)
        gae_lambda = trial.suggest_float("gae_lambda", 0.8, 0.99, step=0.01)
        vf_coef = trial.suggest_float("vf_coef", 0.2, 1.0, step=0.05)
        batch_size = trial.suggest_categorical("batch_size", [64, 128, 256, 512])

        def _make_env():
            env = gym.make(cfg.env_id)
            try:
                env.reset(seed=cfg.seed)
            except Exception:
                pass
            return env
        env = DummyVecEnv([_make_env])

        model = PPO(
            "MlpPolicy",
            env,
            learning_rate=learning_rate,
            n_steps=n_steps,
            batch_size=batch_size,
            gamma=gamma,
            ent_coef=ent_coef,
            clip_range=clip_range,
            gae_lambda=gae_lambda,
            vf_coef=vf_coef,
            verbose=0,
            seed=cfg.seed,
            tensorboard_log=cfg.tb_logdir,
        )

        try:
            model.learn(total_timesteps=cfg.max_train_steps, progress_bar=False)
        except Exception as e:
            _log(f"⚠️ learn中に例外: {e}")
            try:
                env.close()
            except Exception:
                pass
            return 1e9 if cfg.minimize else -1e9

        rets = []
        for _ in range(cfg.n_eval_episodes):
            try:
                mean_r, _ = evaluate_policy(model, env, n_eval_episodes=1, deterministic=True, warn=False)
                if cfg.reward_clip:
                    mean_r = max(-cfg.reward_clip, min(cfg.reward_clip, mean_r))
                rets.append(float(mean_r))
            except Exception as e:
                _log(f"⚠️ evaluate中に例外: {e}")
                rets.append(0.0)

        score = _safe_mean(rets)

        if abs(score) < 1e-12:
            _log("⚠️ 評価が0.0に張り付いています。trial params=" + json.dumps(trial.params, ensure_ascii=False))

        trial.report(score, step=cfg.max_train_steps)
        if trial.should_prune():
            if cfg.max_train_steps >= cfg.allow_prune_after:
                try:
                    env.close()
                except Exception:
                    pass
                raise optuna_mod.TrialPruned()

        try:
            env.close()
        except Exception:
            pass
        return float(score)

    return objective

def run(cfg: OptunaConfig) -> Dict[str, Any]:
    mods = _lazy_imports()
    optuna_mod = mods["optuna"]
    sampler, pruner = _make_sampler_pruner(cfg, optuna_mod)

    direction = "minimize" if cfg.minimize else "maximize"
    _log(f"🎯 Study: {cfg.study_name} ({direction}), storage={cfg.storage_url}, worker={cfg.worker_tag}")
    study = optuna_mod.create_study(
        study_name=cfg.study_name,
        storage=cfg.storage_url,
        direction=direction,
        sampler=sampler,
        pruner=pruner,
        load_if_exists=True,
    )

    objective = make_objective(cfg)
    study.optimize(
        objective,
        n_trials=cfg.n_trials,
        timeout=cfg.timeout_sec,
        gc_after_trial=True,
        n_jobs=1,
        catch=(Exception,),
    )

    best_value = study.best_value if study.best_trial else (math.inf if cfg.minimize else -math.inf)
    best_params = study.best_trial.params if study.best_trial else {}
    _log(f"✅ 最適化完了: best_value={best_value}, best_params={best_params}")

    return {
        "study_name": cfg.study_name,
        "best_value": best_value,
        "best_params": best_params,
        "n_trials": len(study.trials),
        "datetime_utc": datetime.utcnow().isoformat(),
        "worker_tag": cfg.worker_tag,
    }

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Noctria - Optuna最適化実行")
    p.add_argument("--study_name", type=str, default="noctria_rl_ppo")
    p.add_argument("--storage_url", type=str, default=os.getenv("OPTUNA_STORAGE", ""))
    p.add_argument("--n_trials", type=int, default=100)
    p.add_argument("--timeout_sec", type=int, default=None)
    p.add_argument("--n_startup_trials", type=int, default=10)
    p.add_argument("--n_eval_episodes", type=int, default=5)
    p.add_argument("--max_train_steps", type=int, default=100_000)
    p.add_argument("--sampler", type=str, default="tpe", choices=["tpe", "random"])
    p.add_argument("--pruner", type=str, default="median", choices=["median", "sha", "none"])
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--tb_logdir", type=str, default=None)
    p.add_argument("--env_id", type=str, default="CartPole-v1")
    p.add_argument("--reward_clip", type=float, default=None)
    p.add_argument("--minimize", action="store_true")
    p.add_argument("--allow_prune_after", type=int, default=2_000)
    p.add_argument("--worker_tag", type=str, default=f"worker-{os.getenv('HOSTNAME','local')}")
    return p.parse_args()

# ===== Airflow/PythonOperator 用の公開関数 =====
def optimize_main(**context):
    """
    Airflow から直接 import されるエントリポイント。
    - PythonOperator の python_callable に指定可能
    - return 値は XCom に保存される
    """
    # Airflowのparams/op_kwargsのどちらでも拾えるように
    params = (context.get("params") or {}) if isinstance(context, dict) else {}
    # argparse.Namespace を作って既定値＋paramsを適用
    args = argparse.ArgumentParser().parse_args(args=[])
    args.study_name = params.get("study_name", "noctria_rl_ppo")
    args.storage_url = os.environ.get("OPTUNA_STORAGE", params.get("storage_url", ""))
    args.n_trials = int(params.get("n_trials", 100))
    args.timeout_sec = int(params["timeout_sec"]) if "timeout_sec" in params and params["timeout_sec"] is not None else None
    args.n_startup_trials = int(params.get("n_startup_trials", 10))
    args.n_eval_episodes = int(params.get("n_eval_episodes", 5))
    args.max_train_steps = int(params.get("max_train_steps", 100000))
    args.sampler = params.get("sampler", "tpe")
    args.pruner = params.get("pruner", "median")
    args.seed = int(params.get("seed", 42))
    args.tb_logdir = params.get("tb_logdir", None)
    args.env_id = params.get("env_id", "CartPole-v1")
    args.reward_clip = float(params["reward_clip"]) if "reward_clip" in params and params["reward_clip"] is not None else None
    args.minimize = bool(str(params.get("minimize", "false")).lower() in ("1", "true", "yes"))
    args.allow_prune_after = int(params.get("allow_prune_after", 2000))
    # ワーカータグ（task_id を活用してユニーク化）
    ti = context.get("ti")
    task_id = getattr(ti, "task_id", "worker")
    args.worker_tag = params.get("worker_tag", f"worker-{task_id}")

    cfg = build_config(args)
    result = run(cfg)
    # PythonOperator は return を XCom に保存する
    return result

def main():
    args = parse_args()
    cfg = build_config(args)
    result = run(cfg)
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
