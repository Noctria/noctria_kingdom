# airflow_docker/dags/train_prometheus_obs8_dag.py
# -*- coding: utf-8 -*-
"""
Train SB3(PPO) model for Prometheus (obs_dim=8) with hyperparameters from --conf.

受け取れる --conf キー（任意）:
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
- clip_range_vf (float)
- seed (int)
"""

from __future__ import annotations

import os
import sys
import json
import importlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# --- Airflowコンテナ内のsrcを確実にimport可能にする ---
for p in ("/opt/airflow/src", "/opt/airflow"):
    if p not in sys.path:
        sys.path.append(p)

from airflow import DAG
from airflow.operators.python import PythonOperator


def _safe_get(d: Dict[str, Any], key: str, cast, default=None):
    """conf から key を取りつつ型変換。失敗時は default。"""
    if d is None:
        return default
    if key not in d:
        return default
    v = d[key]
    try:
        # Airflow UIから入ると数値が文字列になることがある
        return cast(v)
    except Exception:
        return default


def _build_ppo_hparams(conf: Dict[str, Any]) -> Dict[str, Any]:
    """
    --conf で渡された値から PPO のkwargsを構築（渡されたものだけ）。
    """
    hp: Dict[str, Any] = {}

    # 数値変換用の小ヘルパ
    fint = lambda k: _safe_get(conf, k, int, None)
    fflt = lambda k: _safe_get(conf, k, float, None)

    # 代表的なPPOハイパラ
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
    description="Train SB3 PPO (obs_dim=8) and save with metadata (hyperparams via --conf)",
    start_date=datetime(2025, 8, 1),
    schedule=None,
    catchup=False,
    tags=["training", "prometheus", "obs8", "sb3"],
) as dag:

    def train_and_save_model(**context):
        # 遅延import（DagBag読み込みを軽く＆失敗を局所化）
        from src.utils.model_io import (
            infer_obs_dim_from_env,
            build_model_path,
            atomic_save_model,
        )

        # 1) Env 構築
        prom_env = os.environ.get("PROMETHEUS_ENV")
        if not prom_env or ":" not in prom_env:
            raise ValueError(
                "PROMETHEUS_ENV must be set like 'package.module:ClassName'"
            )
        mod_path, cls_name = prom_env.split(":", 1)
        env_kwargs_str = os.environ.get("PROMETHEUS_ENV_KWARGS", "{}")
        try:
            env_kwargs = json.loads(env_kwargs_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"PROMETHEUS_ENV_KWARGS must be JSON: {e}")

        EnvCls = getattr(importlib.import_module(mod_path), cls_name)
        env = EnvCls(**env_kwargs)

        try:
            # 2) 学習パラメータ（--conf）を収集
            from stable_baselines3 import PPO  # 遅延import

            conf: Dict[str, Any] = (context.get("dag_run").conf or {}) if context else {}
            total_timesteps = _safe_get(conf, "TOTAL_TIMESTEPS", int, None)
            if total_timesteps is None:
                # 環境変数 or 既定
                total_timesteps = int(os.environ.get("TOTAL_TIMESTEPS", 10_000))

            ppo_kwargs = _build_ppo_hparams(conf)

            print("[train] PPO kwargs (from --conf):", json.dumps(ppo_kwargs, ensure_ascii=False))
            print("[train] TOTAL_TIMESTEPS:", total_timesteps)

            # 3) モデル作成＆学習
            model = PPO("MlpPolicy", env, verbose=1, **ppo_kwargs)
            model.learn(total_timesteps=total_timesteps)

            # 4) 保存（obs_dim刻印・メタ出力・latest更新）
            obs_dim = infer_obs_dim_from_env(env)
            save_path = build_model_path(
                base_dir=Path("/opt/airflow/data/models"),
                project="prometheus",
                algo=model.__class__.__name__,
                obs_dim=obs_dim,
                tag=context.get("run_id"),
            )
            # メタにハイパラも刻む
            meta_extra = {
                "total_timesteps": total_timesteps,
                "airflow_dag_run_id": context.get("run_id"),
                "ppo_hyperparams": ppo_kwargs,
            }
            final_path = atomic_save_model(
                model,
                save_path,
                metadata_extra=meta_extra,
                env=env,
                project="prometheus",
            )
            print(f"[OK] saved: {final_path}")
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
