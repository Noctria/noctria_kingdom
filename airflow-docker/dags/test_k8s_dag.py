from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
from datetime import datetime

with DAG(
    dag_id='test_k8s_dag',
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["test", "k8s"],
) as dag:

    k8s_test = KubernetesPodOperator(
        task_id="run_test_pod",
        name="test-pod",
        namespace="default",
        image="alpine",
        cmds=["echo", "Hello from Kubernetes"],
        get_logs=True,
        is_delete_operator_pod=True,
    )
