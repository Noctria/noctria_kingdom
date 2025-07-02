from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
import sys
import os

# 🔧 Airflow内PYTHONPATH（Docker環境でも対応）
sys.path.append("/opt/airflow")

# ✅ MetaAI最適パラメータ適用関数（外部スクリプトからの読み込み）
from scripts.apply_best_params_to_metaai import apply_best_params_to_metaai

# ✅ DAG定義
with DAG(
    dag_id="metaai_apply_dag",
    schedule_interval=None,  # 人の操作または他DAGによるトリガーを想定
    start_date=days_ago(1),
    catchup=False,
    tags=["noctria", "metaai", "retrain"],
    description="📌 MetaAIに最適パラメータを適用する単体DAG",
) as dag:

    apply_metaai_task = PythonOperator(
        task_id="apply_best_params_to_metaai",
        python_callable=apply_best_params_to_metaai,
    )
