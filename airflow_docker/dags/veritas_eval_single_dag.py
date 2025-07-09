# airflow_docker/dags/veritas_eval_single_dag.py

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.python import get_current_context

from datetime import datetime, timedelta
import subprocess

default_args = {
    'owner': 'Veritas',
    'depends_on_past': False,
    'start_date': datetime(2025, 6, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=2),
}

dag = DAG(
    dag_id='veritas_eval_single_dag',
    default_args=default_args,
    description='🔁 単一戦略を評価（スクリプト経由）',
    schedule_interval=None,
    catchup=False,
    tags=['veritas', 'pdca', 'single_eval'],
)

def call_single_eval_script():
    context = get_current_context()
    conf = context.get("dag_run").conf or {}
    strategy_name = conf.get("strategy_name")

    if not strategy_name:
        raise ValueError("❌ strategy_name が conf で指定されていません")

    # 📦 評価スクリプトを subprocess 経由で呼び出し
    subprocess.run(
        ["python3", "/noctria_kingdom/scripts/evaluate_single_strategy.py", strategy_name],
        check=True
    )

# === DAG登録 ===
with dag:
    eval_task = PythonOperator(
        task_id='evaluate_single_strategy_by_script',
        python_callable=call_single_eval_script,
    )
