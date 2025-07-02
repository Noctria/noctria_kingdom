import sys
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

# ✅ PYTHONPATH を補完（Airflowコンテナ内では /opt/airflow がベース）

# ✅ パス集中管理と Lint関数
from core.path_config import _lint_path_config, VERITAS_EVAL_LOG

# === DAG共通設定 ===
default_args = {
    'owner': 'System',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=1),
}

# === DAG定義 ===
dag = DAG(
    dag_id='structure_check_dag',
    description='🧱 パス構成と構造の整合性をLintするDAG',
    default_args=default_args,
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['lint', 'structure', 'system']
)

# === Lint関数 ===
def run_path_lint(**kwargs):
    _lint_path_config(raise_on_error=True)

# === DAGタスク定義 ===
with dag:
    lint_task = PythonOperator(
        task_id='run_path_config_lint',
        python_callable=run_path_lint
    )
