from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from core.strategy_evaluator import evaluate_strategy  # ✅ 共通関数をインポート

def recheck_strategy(**context):
    dag_run = context.get("dag_run")
    if not dag_run or not dag_run.conf:
        raise ValueError("DAG must be triggered with a config including 'strategy_name'")

    strategy_name = dag_run.conf.get("strategy_name")
    if not strategy_name:
        raise ValueError("strategy_name is required in dag_run.conf")

    result = evaluate_strategy(strategy_name)
    return result

default_args = {
    "owner": "Noctria",
    "retries": 0,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    dag_id="veritas_recheck_dag",
    start_date=datetime(2025, 7, 1),
    schedule_interval=None,
    catchup=False,
    default_args=default_args,
    tags=["veritas", "recheck"],
) as dag:

    recheck_task = PythonOperator(
        task_id="recheck_strategy",
        python_callable=recheck_strategy,
        provide_context=True,
    )
