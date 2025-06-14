from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'Noctria',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='noctria_gpu_dag',
    default_args=default_args,
    description='GPU対応: Noctria戦略AIのKubernetesPodOperatorによる実行',
    schedule_interval=None,
    start_date=datetime(2025, 6, 14),
    catchup=False,
    tags=['noctria', 'gpu', 'kubernetes'],
) as dag:

    run_ai_module_gpu = KubernetesPodOperator(
        task_id='run_aurus_singularis_gpu',
        name='aurus-singularis-gpu',
        namespace='default',
        image='noctria/aurus-singularis:latest',  # 🎯 GPU対応AIモジュールのDockerイメージ
        cmds=["python"],
        arguments=["/app/aurus_model.py"],
        resources={
            "limit_gpu": 1,        # ✅ GPUリソースを1つ要求
            "request_memory": "4Gi",
            "request_cpu": "1000m"
        },
        container_resources={
            "limits": {"nvidia.com/gpu": "1"},
            "requests": {"nvidia.com/gpu": "1"}
        },
        is_delete_operator_pod=True,
        get_logs=True,
    )
