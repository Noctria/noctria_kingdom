# airflow_docker/dags/train_prometheus_obs8_dag.py
# -*- coding: utf-8 -*-
"""
Train SB3(PPO) model for Prometheus (obs_dim=8) with hyperparameters from --conf,
then evaluate N episodes and stamp results into metadata.json.

--conf keys (optional):
- TOTAL_TIMESTEPS (int)
- learning_rate (float)
- n_steps (int)
- batch_size (int)
- n_epochs (int)
- gamma (float)
- gae_lambda (float)
- ent_coef (float)
- vf_coef (float)
- max_grad_norm (float)
- clip_range (float)
- clip_range_vf (float)   # SB3>=2.0
- seed (int)

- eval_n_episodes (int, default: 5)
- eval_deterministic (bool or "true"/"false", default: true)
"""

from __future__ import annotations

import os
import sys
import json
import importlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# --- ensure src importable in Airflow containers ---
for p in ("/opt/airflow/src", "/opt/airflow"):
    if p not in sys.path:
        sys.path.append(p)

from airflow import DAG
from airflow.operators.python import PythonOperator


def _safe_get(d: Dict[str, Any], key: str, cast, default=None):
    if d is None or key not in d:
        return default
    v = d[key]
    try:
        return cast(v)
    except Exception:
        # bool は文字列で来ることがある
        if cast is bool and isinstance(v, str):
            return v.strip().lower() in ("1", "true", "yes", "y", "on")
        return default


def _build_ppo_hparams(conf: Dict[str, Any]) -> Dict[str, Any]:
    hp: Dict[str, Any] = {}
    for k, cvt in [
        ("learning_rate", float),
        ("n_steps", int),
        ("batch_size", int),
        ("n_epochs", int),
        ("gamma", float),
        ("gae_lambda", float),
        ("ent_coef", float),
        ("vf_coef", float),
        ("max_grad_norm", float),
        ("clip_range", float),
        ("clip_range_vf", float),  # SB3>=2.0
        ("seed", int),
    ]:
        v = _safe_get(conf, k, cvt, None)
        if v is not None:
            hp[k] = v
    return hp


with DAG(
    dag_id="train_prometheus_obs8",
    description="Train SB3 PPO (obs=8) → evaluate → stamp metadata",
    start_date=datetime(2025, 8, 1),
    schedule=None,
    catchup=False,
    tags=["training", "prometheus", "obs8", "sb3"],
) as dag:

    def train_and_save_model(**context) -> str:
        # delayed imports
        from src.utils.model_io import (
            infer_obs_dim_from_env,
            build_model_path,
            atomic_save_model,
        )
        from stable_baselines3 import PPO

        # Env build
        prom_env = os.environ.get("PROMETHEUS_ENV")
        if not prom_env or ":" not in prom_env:
            raise ValueError("PROMETHEUS_ENV must be 'module.path:ClassName'")
        mod_path, cls_name = prom_env.split(":", 1)
        env_kwargs = json.loads(os.environ.get("PROMETHEUS_ENV_KWARGS", "{}"))
        EnvCls = getattr(importlib.import_module(mod_path), cls_name)
        env = EnvCls(**env_kwargs)

        try:
            conf: Dict[str, Any] = (context.get("dag_run").conf or {}) if context else {}
            total_timesteps = _safe_get(conf, "TOTAL_TIMESTEPS", int, None)
            if total_timesteps is None:
                total_timesteps = int(os.environ.get("TOTAL_TIMESTEPS", 10_000))
            ppo_kwargs = _build_ppo_hparams(conf)

            print("[train] PPO kwargs:", json.dumps(ppo_kwargs, ensure_ascii=False))
            print("[train] TOTAL_TIMESTEPS:", total_timesteps)

            model = PPO("MlpPolicy", env, verbose=1, **ppo_kwargs)
            model.learn(total_timesteps=total_timesteps)

            # save
            obs_dim = infer_obs_dim_from_env(env)
            save_path = build_model_path(
                base_dir=Path("/opt/airflow/data/models"),
                project="prometheus",
                algo=model.__class__.__name__,
                obs_dim=obs_dim,
                tag=context.get("run_id"),
            )
            meta_extra = {
                "total_timesteps": total_timesteps,
                "airflow_dag_run_id": context.get("run_id"),
                "ppo_hyperparams": ppo_kwargs,
            }
            final_dir = atomic_save_model(
                model,
                save_path,
                metadata_extra=meta_extra,
                env=env,
                project="prometheus",
            )
            print(f"[OK] saved: {final_dir}")
            # return for downstream via XCom
            return str(final_dir)
        finally:
            try:
                env.close()
            except Exception:
                pass

    def evaluate_and_stamp(**context) -> None:
        """
        Load saved model, evaluate N episodes, and update metadata.json.
        """
        from stable_baselines3 import PPO

        # pull model dir from XCom (train task return)
        ti = context["ti"]
        model_dir = ti.xcom_pull(task_ids="train_and_save_model")
        if not model_dir:
            raise RuntimeError("No model_dir from XCom")

        model_dir = str(model_dir)
        meta_path = Path(model_dir) / "metadata.json"
        model_zip = Path(model_dir) / "model.zip"

        # read conf
        conf: Dict[str, Any] = (context.get("dag_run").conf or {}) if context else {}
        n_episodes = _safe_get(conf, "eval_n_episodes", int, 5)
        deterministic = _safe_get(conf, "eval_deterministic", bool, True)

        # rebuild Env with same kwargs
        prom_env = os.environ.get("PROMETHEUS_ENV")
        if not prom_env or ":" not in prom_env:
            raise ValueError("PROMETHEUS_ENV must be 'module.path:ClassName'")
        mod_path, cls_name = prom_env.split(":", 1)
        env_kwargs = json.loads(os.environ.get("PROMETHEUS_ENV_KWARGS", "{}"))
        EnvCls = getattr(importlib.import_module(mod_path), cls_name)

        env = EnvCls(**env_kwargs)
        model = PPO.load(str(model_zip))

        import numpy as np

        ep_rewards = []
        ep_lengths = []
        wins = 0

        def _reset(e):
            out = e.reset()
            # gymnasium: (obs, info) / gym: obs
            return out[0] if isinstance(out, tuple) and len(out) == 2 else out

        def _step(e, action):
            out = e.step(action)
            # gymnasium: (obs, reward, terminated, truncated, info)
            if len(out) == 5:
                obs, rew, terminated, truncated, info = out
                done = bool(terminated or truncated)
                return obs, rew, done, info
            # gym: (obs, reward, done, info)
            return out

        try:
            for ep in range(int(n_episodes)):
                obs = _reset(env)
                done = False
                total = 0.0
                steps = 0
                while not done:
                    action, _ = model.predict(obs, deterministic=deterministic)
                    obs, rew, done, _info = _step(env, action)
                    total += float(rew)
                    steps += 1
                ep_rewards.append(total)
                ep_lengths.append(steps)
                if total > 0:
                    wins += 1

            avg = float(np.mean(ep_rewards)) if ep_rewards else 0.0
            std = float(np.std(ep_rewards)) if ep_rewards else 0.0
            ep_len_mean = float(np.mean(ep_lengths)) if ep_lengths else 0.0
            win_rate = float(wins) / max(1, len(ep_rewards))

            print(f"[eval] episodes={n_episodes} avg={avg:.4f} std={std:.4f} win_rate={win_rate:.3f} len={ep_len_mean:.1f}")

            # update metadata.json
            meta = {}
            if meta_path.exists():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta.setdefault("evaluation", {})
            meta["evaluation"].update({
                "evaluated_at_utc": datetime.utcnow().isoformat(),
                "n_episodes": int(n_episodes),
                "deterministic": bool(deterministic),
                "avg_reward": avg,
                "std_reward": std,
                "win_rate": win_rate,
                "ep_len_mean": ep_len_mean,
            })
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[OK] stamped evaluation into: {meta_path}")

        finally:
            try:
                env.close()
            except Exception:
                pass

    train_task = PythonOperator(
        task_id="train_and_save_model",
        python_callable=train_and_save_model,
        provide_context=True,
    )

    eval_task = PythonOperator(
        task_id="evaluate_and_stamp",
        python_callable=evaluate_and_stamp,
        provide_context=True,
    )

    train_task >> eval_task
