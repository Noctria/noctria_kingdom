from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
from datetime import timedelta
from core.path_config import EXECUTION_DIR

default_args = {
    'owner': 'noctria',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'email_on_failure': False,
    'email_on_retry': False,
}

with DAG(
    dag_id="veritas_replay_dag",
    description="PDCAログから再送実行する専用DAG",
    start_date=days_ago(1),
    schedule_interval=None,
    catchup=False,
    default_args=default_args,
    params={"log_path": ""},  # GUI/APIから渡すログパス
    tags=["veritas", "replay", "pdca"]
) as dag:

    replay_from_log = BashOperator(
        task_id="replay_order_from_log",
        bash_command=(
            f"PYTHONPATH=/opt/airflow python {EXECUTION_DIR}/generate_order_json.py "
            "--from-log '{{{{ params.log_path }}}}'"
        )
    )
