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

    generate_task = BashOperator(
        task_id="generate_strategy",
        bash_command="python3 /noctria_kingdom/scripts/generate_strategy_file.py"
    )

    evaluate_task = BashOperator(
        task_id="evaluate_strategies",
        bash_command="python3 /noctria_kingdom/scripts/evaluate_generated_strategies.py market_data.csv"
    )

    push_task = BashOperator(
        task_id="push_adopted_strategies",
        bash_command="python3 /noctria_kingdom/scripts/github_push.py"
    )

    generate_task >> evaluate_task >> push_task
