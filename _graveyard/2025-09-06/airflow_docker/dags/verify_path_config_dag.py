from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "Noctria",
    "retries": 1,
    "retry_delay": timedelta(minutes=3),
}

with DAG(
    dag_id="verify_path_config_dag",
    description="🛡️ Noctria Kingdom 構成検査用DAG",
    default_args=default_args,
    schedule_interval=None,
    start_date=datetime(2025, 7, 1),
    catchup=False,
    tags=["noctria", "integrity", "structure"],
) as dag:

    verify_path_integrity = BashOperator(
        task_id="verify_path_integrity",
        bash_command="python3 tools/verify_path_config.py --strict --show-paths"
    )
