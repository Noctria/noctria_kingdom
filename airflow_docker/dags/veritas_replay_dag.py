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
    description="PDCAログから再送実行する専用DAG（統治ID・理由・呼出元必須）",
    start_date=days_ago(1),
    schedule=None,
    catchup=False,
    default_args=default_args,
    params={
        "log_path": "",       # 必須
        "decision_id": "",    # 必須
        "reason": "",         # 任意
        "caller": "",         # 任意
    },
    tags=["veritas", "replay", "pdca"]
) as dag:

    replay_from_log = BashOperator(
        task_id="replay_order_from_log",
        bash_command=(
            # 必須パラメータバリデーション
            "if [ -z '{{ params.decision_id }}' ]; then echo 'decision_id必須'; exit 1; fi && "
            "if [ -z '{{ params.log_path }}' ]; then echo 'log_path必須'; exit 1; fi && "
            f"PYTHONPATH=/opt/airflow python {EXECUTION_DIR}/generate_order_json.py "
            "--from-log '{{{{ params.log_path }}}}' "
            "--decision-id '{{{{ params.decision_id }}}}' "
            "--reason '{{{{ params.reason }}}}' "
            "--caller '{{{{ params.caller }}}}'"
        )
    )
