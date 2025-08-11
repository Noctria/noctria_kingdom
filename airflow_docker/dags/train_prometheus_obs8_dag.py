# airflow_docker/dags/train_prometheus_obs8_dag.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, os, importlib
from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

from src.utils.model_io import (
    infer_obs_dim_from_env,
    build_model_path,
    atomic_save_model,
)

with DAG(
    dag_id="train_prometheus_obs8",
    description="Train SB3 model (obs_dim=8 aware) and save with metadata",
    start_date=datetime(2025, 8, 1),
    schedule=None,
    catchup=False,
    tags=["training", "prometheus", "obs8", "sb3"],
) as dag:

    def train_and_save(**context):
        # 1) Env 構築
        mod_path, cls_name = os.environ["PROMETHEUS_ENV"].split(":")
        env_kwargs = json.loads(os.environ.get("PROMETHEUS_ENV_KWARGS", "{}"))
        EnvCls = getattr(importlib.import_module(mod_path), cls_name)
        env = EnvCls(**env_kwargs)

        # 2) 学習
        from stable_baselines3 import PPO
        total_timesteps = int(
            (context.get("dag_run").conf or {}).get("TOTAL_TIMESTEPS", os.environ.get("TOTAL_TIMESTEPS", 10_000))
        )
        model = PPO("MlpPolicy", env, verbose=1)
        model.learn(total_timesteps=total_timesteps)

        # 3) 保存（obs_dim刻印・メタ出力・latest更新）
        obs_dim = infer_obs_dim_from_env(env)
        save_path = build_model_path(
            base_dir=Path("/opt/airflow/data/models"),
            project="prometheus",
            algo=model.__class__.__name__,
            obs_dim=obs_dim,
            tag=context.get("run_id"),
        )
        final_path = atomic_save_model(
            model,
            save_path,
            metadata_extra={
                "total_timesteps": total_timesteps,
                "airflow_dag_run_id": context.get("run_id"),
            },
            env=env,
            project="prometheus",
        )
        print(f"[OK] saved: {final_path}")
        print(f"[OK] meta: {final_path.with_suffix('.meta.json')}")
        print(f"[OK] latest link dir: {final_path.parent}")
        return str(final_path)

    PythonOperator(
        task_id="train_and_save_model",
        python_callable=train_and_save,
        provide_context=True,
        doc="Train SB3(PPO) on PROMETHEUS_ENV and save with obs_dim-aware path",
    )
