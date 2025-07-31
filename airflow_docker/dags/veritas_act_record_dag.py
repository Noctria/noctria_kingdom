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
    # Airflow confからパラメータ受信
    conf = kwargs.get("dag_run").conf if kwargs.get("dag_run") else {}
    decision_id = conf.get("decision_id", "NO_DECISION_ID")
    reason = conf.get("reason", "理由未指定")
    caller = conf.get("caller", "unknown")
    print(f"⚙️ [decision_id:{decision_id}] 実行中: {SCRIPT_PATH}｜理由: {reason}｜呼出元: {caller}")

    # バリデーション（王API経由のみ許可）
    if decision_id == "NO_DECISION_ID":
        raise ValueError("統治ID（decision_id）が指定されていません！Noctria王API経由のみ許可")

    # サブスクリプトにすべての情報を引数で渡す
    cmd = f"python {SCRIPT_PATH} \"{decision_id}\" \"{reason}\" \"{caller}\""
    exit_code = os.system(cmd)
    if exit_code != 0:
        raise RuntimeError(f"record_act_log.py 実行失敗: exit code {exit_code}")

with DAG(
    dag_id="veritas_act_record_dag",
    default_args=default_args,
    description="Veritas: 採用戦略をActログに記録（統治ID必須）",
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
