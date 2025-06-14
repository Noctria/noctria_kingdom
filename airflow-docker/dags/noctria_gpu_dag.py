from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from datetime import datetime, timedelta

# ✅ DAG設定
default_args = {
    'owner': 'Noctria',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    dag_id='noctria_gpu_dag',
    default_args=default_args,
    description='Noctria KingdomによるGPUトレーニングDAG（KubernetesPodOperator使用）',
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'gpu', 'k8s'],
)

# ✅ GPU対応のTensorFlow Podを起動してGPU確認
gpu_task = KubernetesPodOperator(
    task_id='gpu_training_task',
    name='noctria-gpu-task',
    namespace='default',
    image='tensorflow/tensorflow:latest-gpu',
    cmds=["python", "-c"],
    arguments=["import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"],
    container_resources={
        'limits': {'nvidia.com/gpu': '1'}  # ✅ GPUを1つ要求
    },
    get_logs=True,
    is_delete_operator_pod=True,
    in_cluster=False,  # ✅ 外部接続用
    config_file='/home/airflow/.kube/config',  # ✅ Airflowコンテナ内のパス
    dag=dag,
)
