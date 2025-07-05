from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from core.path_config import VERITAS_GENERATE_SCRIPT, VERITAS_EVALUATE_SCRIPT, GITHUB_PUSH_SCRIPT
import runpy

# ✅ ログユーティリティ
from scripts.log_pdca_result import log_pdca_step

default_args = {
    'owner': 'Veritas',
    'depends_on_past': False,
    'start_date': datetime(2025, 6, 1),
    'retries': 0,
}

dag = DAG(
    dag_id="veritas_pdca_dag",
    description="🔁 Veritas自動戦略PDCAループ",
    default_args=default_args,
    schedule_interval=None,
    catchup=False,
)

def run_generate():
    log_pdca_step("Plan", "Start", "戦略生成開始")
    runpy.run_path(VERITAS_GENERATE_SCRIPT)
    log_pdca_step("Plan", "Success", "戦略生成完了")

def run_evaluate():
    log_pdca_step("Check", "Start", "評価開始")
    runpy.run_path(VERITAS_EVALUATE_SCRIPT)
    log_pdca_step("Check", "Success", "評価完了")

def run_push():
    log_pdca_step("Act", "Start", "採用戦略Push")
    runpy.run_path(GITHUB_PUSH_SCRIPT)
    log_pdca_step("Act", "Success", "Push完了")

with dag:
    generate_task = PythonOperator(task_id="generate", python_callable=run_generate)
    evaluate_task = PythonOperator(task_id="evaluate", python_callable=run_evaluate)
    push_task = PythonOperator(task_id="push", python_callable=run_push)

    generate_task >> evaluate_task >> push_task
