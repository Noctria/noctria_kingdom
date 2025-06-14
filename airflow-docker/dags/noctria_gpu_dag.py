from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from datetime import datetime, timedelta

# DAGの基本設定
default_args = {
    'owner': 'Noctria',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# DAG定義
dag = DAG(
    dag_id='noctria_gpu_dag',
    default_args=default_args,
    description='Noctria KingdomによるGPUトレーニングDAG（pod_template_file使用）',
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'gpu', 'k8s'],
)

# KubernetesPodOperatorの設定
gpu_task = KubernetesPodOperator(
    task_id='gpu_training_task',
    name='noctria-gpu-task',
    namespace='default',
    in_cluster=False,  # ホストの kubeconfig を使用
    config_file='/opt/airflow/kubeconfig_final.yaml',  # ✅ kubeconfigのパスを修正済み
    get_logs=True,
    is_delete_operator_pod=True,
    pod_template_file='/opt/airflow/pod_templates/gpu_job.yaml',  # ✅ GPU用テンプレート
    dag=dag,
)
