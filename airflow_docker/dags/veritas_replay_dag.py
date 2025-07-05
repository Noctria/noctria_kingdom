from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
from datetime import datetime
from core.path_config import EXECUTION_DIR

# ========================================
# 🔁 再送専用DAG（PDCAログからEA命令を復元）
# ========================================

with DAG(
    dag_id="veritas_replay_dag",
    description="PDCAログから再送実行する専用DAG",
    start_date=days_ago(1),
    schedule_interval=None,
    catchup=False,
    params={"log_path": ""},  # GUI/APIから渡すログパス
    tags=["veritas", "replay", "pdca"]
) as dag:

    replay_from_log = BashOperator(
        task_id="replay_order_from_log",
        bash_command=(
            f"PYTHONPATH=/opt/airflow python {EXECUTION_DIR}/generate_order_json.py "
            "--from-log '{{ params.log_path }}'"
        )
    )
