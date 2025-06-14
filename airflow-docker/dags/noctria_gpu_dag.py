from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from datetime import datetime, timedelta

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
    description='Noctria KingdomによるGPUトレーニングDAG（pod_template_file使用）',
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'gpu', 'k8s'],
)

gpu_task = KubernetesPodOperator(
    task_id='gpu_training_task',
    name='noctria-gpu-task-{{ ts_nodash }}',  # リトライ対応
    namespace='airflow',  # namespaceを統一
    in_cluster=False,
    config_file='/opt/airflow/kubeconfig_final.yaml',
    pod_template_file='/opt/airflow/pod_templates/gpu_job.yaml',
    get_logs=True,
    log_events_on_failure=True,
    is_delete_operator_pod=True,
    retries=1,
    retry_delay=timedelta(minutes=5),
    dag=dag,
)
