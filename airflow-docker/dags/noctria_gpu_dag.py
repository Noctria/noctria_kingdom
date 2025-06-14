# /opt/airflow/dags/noctria_gpu_dag.py

import sys
sys.path.append('/opt/airflow')  # core や strategies をパスに追加

from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'Noctria',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='noctria_gpu_dag',
    default_args=default_args,
    description='GPUノード上でCUDAとnvidia-smiを検証するK8s DAG',
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'gpu', 'kubernetes'],
) as dag:

    gpu_check_task = KubernetesPodOperator(
        task_id='gpu_check',
        name='gpu-check-pod',
        namespace='default',  # 必要に応じて変更
        image='nvidia/cuda:12.2.0-base-ubuntu22.04',
        cmds=["nvidia-smi"],
        get_logs=True,
        is_delete_operator_pod=True,
        resources={
            'request_gpu': '1',  # KubernetesでGPU割当をリクエスト
        },
    )
