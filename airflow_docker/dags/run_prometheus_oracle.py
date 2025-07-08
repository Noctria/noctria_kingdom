from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import subprocess

def run_oracle():
    subprocess.run(["python3", "strategies/prometheus_oracle.py"], check=True)

with DAG(
    dag_id="prometheus_oracle_dag",
    start_date=datetime(2025, 7, 1),
    schedule_interval=None,
    catchup=False,
    tags=["oracle", "prediction"]
) as dag:
    run_oracle_task = PythonOperator(
        task_id="run_oracle",
        python_callable=run_oracle
    )
