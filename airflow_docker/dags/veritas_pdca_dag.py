# airflow_docker/dags/veritas_pdca_dag.py

import os
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'Veritas',
    'depends_on_past': False,
    'start_date': datetime(2025, 6, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=1),
}

dag = DAG(
    dag_id="veritas_pdca_dag",
    description="🔁 Veritas自動戦略生成・評価・採用PDCAループ",
    default_args=default_args,
    schedule_interval=None,
    catchup=False,
    tags=["veritas", "pdca", "autoloop"]
)

with dag:

    # ステップ 1: 戦略生成スクリプト
    generate_task = BashOperator(
        task_id="generate_strategy",
        bash_command="python3 /noctria_kingdom/airflow_docker/scripts/generate_strategy_file.py"
    )

    # ステップ 2: 戦略評価・採用判定
    evaluate_task = BashOperator(
        task_id="evaluate_strategies",
        bash_command="python3 /noctria_kingdom/airflow_docker/scripts/evaluate_generated_strategies.py market_data.csv"
    )

    # ステップ 3: 採用戦略を GitHub に push
    push_task = BashOperator(
        task_id="push_adopted_strategies_to_github",
        bash_command="python3 /noctria_kingdom/scripts/github_push.py"
    )

    generate_task >> evaluate_task >> push_task
