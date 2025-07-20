from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import sys
import os

from core.path_config import VERITAS_DIR

SCRIPT_PATH = VERITAS_DIR / "record_act_log.py"

default_args = {
    "owner": "Noctria",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}

def run_record_act_log(**kwargs):
    # Airflowのconf（理由等）受信
    conf = kwargs.get("dag_run").conf if kwargs.get("dag_run") else {}
    reason = conf.get("reason", "理由未指定")
    print(f"⚙️ 実行中: {SCRIPT_PATH}｜理由: {reason}")

    # record_act_log.pyへ理由も引数で渡す
    exit_code = os.system(f"python {SCRIPT_PATH} \"{reason}\"")
    if exit_code != 0:
        raise RuntimeError(f"record_act_log.py 実行失敗: exit code {exit_code}")

with DAG(
    dag_id="veritas_act_record_dag",
    default_args=default_args,
    description="Veritas: 採用戦略をActログに記録",
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["veritas", "act", "pdca"],
) as dag:

    record_act = PythonOperator(
        task_id="record_act_log",
        python_callable=run_record_act_log,
        provide_context=True
    )

    record_act
