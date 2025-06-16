from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

with DAG(
    dag_id='test_windows_gpu_dag',
    start_date=datetime(2025, 6, 17),
    schedule_interval=None,
    catchup=False,
    tags=["test", "windows", "gpu"],
) as dag:

    run_windows_script = BashOperator(
        task_id='run_gpu_test_on_windows',
        bash_command='powershell.exe -Command "python \\"E:\\\\test_gpu_windows.py\\""',
    )
