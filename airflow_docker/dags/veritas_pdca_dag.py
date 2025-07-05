from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import runpy

# ✅ パス一元管理
from core.path_config import (
    VERITAS_GENERATE_SCRIPT,
    VERITAS_EVALUATE_SCRIPT,
    GENERATE_ORDER_SCRIPT,  # ← 追加済みであることを確認
    GITHUB_PUSH_SCRIPT,
    MARKET_DATA_CSV
)

# === DAG共通設定 ===
default_args = {
    'owner': 'Veritas',
    'depends_on_past': False,
    'start_date': datetime(2025, 6, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=1),
}

dag = DAG(
    dag_id="veritas_pdca_dag",
    description="🔁 Veritas自動戦略生成・評価・EA命令生成・GitHub反映までのPDCAループ",
    default_args=default_args,
    schedule_interval=None,
    catchup=False,
    tags=["veritas", "pdca", "autoloop"]
)

# === 各ステップのPython呼び出し関数 ===

def run_generate():
    print("🧠 Veritas戦略生成開始")
    runpy.run_path(VERITAS_GENERATE_SCRIPT)

def run_evaluate():
    print("📊 Veritas戦略評価開始")
    runpy.run_path(VERITAS_EVALUATE_SCRIPT, run_name="__main__")

def run_generate_order():
    print("📦 EA命令ファイル出力開始")
    runpy.run_path(GENERATE_ORDER_SCRIPT, run_name="__main__")

def run_push():
    print("🚀 採用戦略のGitHub Push開始")
    runpy.run_path(GITHUB_PUSH_SCRIPT)

# === DAGに登録 ===

with dag:
    generate_task = PythonOperator(
        task_id="generate_strategy",
        python_callable=run_generate
    )

    evaluate_task = PythonOperator(
        task_id="evaluate_strategies",
        python_callable=run_evaluate
    )

    generate_order_task = PythonOperator(
        task_id="generate_order_json",
        python_callable=run_generate_order
    )

    push_task = PythonOperator(
        task_id="push_adopted_strategies",
        python_callable=run_push
    )

    # 🔁 タスクフロー
    generate_task >> evaluate_task >> generate_order_task >> push_task
