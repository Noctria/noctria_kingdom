from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

with DAG(
    dag_id="noctria_kingdom_pdca",
    schedule_interval="@daily",
    start_date=days_ago(1),
    catchup=False
) as dag:
    
    optimize_worker_1 = BashOperator(
        task_id="optimize_worker_1",
        bash_command="python3 /opt/airflow/scripts/optimize_params_with_optuna.py"
    )

    optimize_worker_2 = BashOperator(
        task_id="optimize_worker_2",
        bash_command="python3 /opt/airflow/scripts/optimize_params_with_optuna.py"
    )

    optimize_worker_3 = BashOperator(
        task_id="optimize_worker_3",
        bash_command="python3 /opt/airflow/scripts/optimize_params_with_optuna.py"
    )

    # 最終結果の適用タスク例
    apply_best_params = BashOperator(
        task_id="apply_best_params",
        bash_command="python3 /opt/airflow/scripts/apply_best_params.py"
    )

    [optimize_worker_1, optimize_worker_2, optimize_worker_3] >> apply_best_params
