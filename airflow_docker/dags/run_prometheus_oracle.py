# run_prometheus_oracle.py

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import subprocess

# 📈 PrometheusOracleの予測実行
def run_prometheus_oracle():
    subprocess.run(["python3", "strategies/prometheus_oracle.py"], check=True)

with DAG(
    dag_id="run_prometheus_oracle",
    start_date=datetime(2025, 7, 1),
    schedule_interval=None,  # GUIから手動実行のみ
    catchup=False,
    tags=["oracle", "prediction"]
) as dag:
    task = PythonOperator(
        task_id="predict_with_oracle",
        python_callable=run_prometheus_oracle
    )
