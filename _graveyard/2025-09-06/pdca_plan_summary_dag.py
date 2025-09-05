# airflow_docker/dags/pdca_plan_summary_dag.py

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
from datetime import datetime

default_args = {
    "owner": "noctria",
    "depends_on_past": False,
    "start_date": days_ago(1),
    "retries": 0,
}

with DAG(
    dag_id="pdca_plan_summary_dag",
    description="PDCA-Plan自動要因分析＆根拠サマリー自動生成バッチ",
    schedule_interval="0 7 * * *",  # 毎日7時
    default_args=default_args,
    catchup=False,
    tags=["pdca", "plan", "ai", "summary"],
) as dag:

    make_plan_summary = BashOperator(
        task_id="make_plan_summary",
        bash_command="PYTHONPATH=/opt/airflow/src python /opt/airflow/src/plan_data/run_pdca_plan_workflow.py",
        env={"PYTHONPATH": "/opt/airflow/src"}
    )
