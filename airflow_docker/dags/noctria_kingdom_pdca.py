from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

# === DAG基本設定 ===
default_args = {
    'owner': 'Noctria',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
}

with DAG(
    dag_id="noctria_kingdom_pdca",
    description="🔄 Noctria王国のPDCA戦略最適化ループ（Optuna並列 + 適用）",
    default_args=default_args,
    schedule_interval="@daily",
    start_date=days_ago(1),
    catchup=False,
    tags=["noctria", "optuna", "pdca"]
) as dag:

    # 🛡️ 最適化ワーカーたち（王国の戦略軍団）
    optimize_worker_1 = BashOperator(
        task_id="optimize_worker_1",
        bash_command="python3 /noctria_kingdom/airflow_docker/scripts/optimize_params_with_optuna.py"
    )

    optimize_worker_2 = BashOperator(
        task_id="optimize_worker_2",
        bash_command="python3 /noctria_kingdom/airflow_docker/scripts/optimize_params_with_optuna.py"
    )

    optimize_worker_3 = BashOperator(
        task_id="optimize_worker_3",
        bash_command="python3 /noctria_kingdom/airflow_docker/scripts/optimize_params_with_optuna.py"
    )

    # 👑 Leviaが最適戦略を王国に奏上
    apply_best_params = BashOperator(
        task_id="apply_best_params",
        bash_command="python3 /noctria_kingdom/airflow_docker/scripts/apply_best_params_to_metaai.py"
    )

    # 🧩 流れ：並列最適化 → 集約 → 適用
    [optimize_worker_1, optimize_worker_2, optimize_worker_3] >> apply_best_params
