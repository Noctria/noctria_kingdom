# airflow_docker/dags/noctria_backtest_dag.py
from __future__ import annotations
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import json, os

def dummy_backtest(**context):
    """疎通確認用: confを表示してダミー結果を書き出す"""
    run_id = context["run_id"]
    conf = context["dag_run"].conf or {}

    print("=== Backtest (dummy) ===")
    print(json.dumps(conf, ensure_ascii=False, indent=2))

    outdir = f"/opt/airflow/backtests/{run_id}"
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "result.json"), "w", encoding="utf-8") as f:
        json.dump(
            {"ok": True, "msg": "Dummy backtest succeeded", "conf": conf},
            f, ensure_ascii=False, indent=2
        )

    return {"result_path": f"{outdir}/result.json"}

default_args = {
    "owner": "noctria",
    "retries": 0,
}

with DAG(
    dag_id="noctria_backtest_dag",
    default_args=default_args,
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,            # API専用
    catchup=False,
    dagrun_timeout=timedelta(minutes=5),
    tags=["noctria", "backtest", "dummy"],
) as dag:

    run = PythonOperator(
        task_id="dummy_backtest",
        python_callable=dummy_backtest,
        provide_context=True,
    )
