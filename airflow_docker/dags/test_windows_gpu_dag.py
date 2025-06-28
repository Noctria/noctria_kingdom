from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

with DAG(
    dag_id="test_tensorflow_gpu_from_windows",
    start_date=datetime(2025, 6, 1),
    schedule_interval=None,
    catchup=False,
) as dag:

    test_gpu = BashOperator(
        task_id="run_tensorflow_gpu_test",
        bash_command=r"E:\venv_windows_gpu\Scripts\python.exe E:\test_gpu_tf.py"
    )
