from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
from datetime import timedelta, datetime

default_args = {
    "owner": "Noctria",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="noctria_kingdom_pdca_dag",
    description="🏰 Noctria KingdomのPDCAサイクル統合DAG（Optuna最適化 → MetaAI再学習 → 戦略適用）",
    default_args=default_args,
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=["noctria", "kingdom", "pdca"],
) as dag:

    # 🔍 Step 1: Optunaによる戦略最適化
    optimize_worker_1 = BashOperator(
        task_id="optimize_worker_1",
        bash_command=(
            "echo '⚙️ Starting Optuna optimization...'; "
            "python3 /opt/airflow/scripts/optimize_params_with_optuna.py"
        ),
        dag=dag,
    )

    # 📘 Step 2: best_params.jsonをMetaAIに適用して再学習
    apply_to_metaai = BashOperator(
        task_id="apply_best_params_to_metaai",
        bash_command=(
            "echo '📡 Applying best_params to MetaAI...'; "
            "python3 /opt/airflow/scripts/apply_best_params_to_metaai.py"
        ),
        dag=dag,
    )

    # 🏁 Step 3: 王国システムへ最適戦略反映
    apply_to_kingdom = BashOperator(
        task_id="apply_best_params_to_kingdom",
        bash_command=(
            "echo '👑 Applying parameters to kingdom...'; "
            "python3 /opt/airflow/scripts/apply_best_params.py"
        ),
        dag=dag,
    )

    # DAGフロー定義: 最適化 → MetaAI再学習 → Kingdom適用
    optimize_worker_1 >> apply_to_metaai >> apply_to_kingdom
