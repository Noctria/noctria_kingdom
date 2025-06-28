import os
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

# === DAGの基本設定 ===
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
    description="🔁 Veritas自動戦略生成・評価・採用PDCAループ",
    default_args=default_args,
    schedule_interval=None,
    catchup=False,
    tags=["veritas", "pdca", "autoloop"]
)

# === ステップ 1: 戦略ファイルの自動生成 ===
def generate_strategy():
    from veritas.generate_strategy_file import generate_strategy_file
    generate_strategy_file("veritas_strategy")

# === ステップ 2: 生成戦略の評価・採用判定 ===
def evaluate_strategies():
    from dags.veritas_eval_dag import evaluate_and_adopt_strategies
    evaluate_and_adopt_strategies()

# === DAGタスク定義 ===
with dag:
    generate_task = PythonOperator(
        task_id="generate_strategy",
        python_callable=generate_strategy
    )

    evaluate_task = PythonOperator(
        task_id="evaluate_and_adopt",
        python_callable=evaluate_strategies
    )

    generate_task >> evaluate_task
