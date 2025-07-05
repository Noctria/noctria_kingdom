# airflow_docker/dags/veritas_replay_dag.py
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime
from core.path_config import EXECUTION_DIR

with DAG(
    dag_id="veritas_replay_dag",
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,
    catchup=False,
    params={"log_path": "/path/to/log.json"},
    tags=["veritas", "replay"]
) as dag:

    replay_order = BashOperator(
        task_id="replay_order_from_log",
        bash_command=(
            f"PYTHONPATH=/opt/airflow python {EXECUTION_DIR}/generate_order_json.py "
            "--from-log '{{ params.log_path }}'"
        )
    )
