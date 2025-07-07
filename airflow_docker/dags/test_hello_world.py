from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

with DAG(
    dag_id="test_hello_world",
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["debug"]
) as dag:
    t1 = BashOperator(
        task_id="say_hello",
        bash_command="echo 'Hello from Airflow'"
    )
