from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

with DAG(
    dag_id="noctria_kingdom_pdca_dag",
    description="🏰 Noctria KingdomのPDCAサイクル統合DAG（Optuna最適化→MetaAI再学習→適用）",
    schedule_interval=None,
    start_date=days_ago(1),
    catchup=False,
    tags=["noctria", "kingdom", "pdca"]
) as dag:

    # 🔍 最適化ワーカー
    optimize_worker_1 = BashOperator(
        task_id="optimize_worker_1",
        bash_command="python3 /opt/airflow/scripts/optimize_params_with_optuna.py"
    )

    # ✅ best_params.json の結果を MetaAI に適用し再学習
    apply_to_metaai = BashOperator(
        task_id="apply_best_params_to_metaai",
        bash_command="python3 /opt/airflow/scripts/apply_best_params_to_metaai.py"
    )

    # ✅ 最終的に王国システムへ反映
    apply_to_kingdom = BashOperator(
        task_id="apply_best_params_to_kingdom",
        bash_command="python3 /opt/airflow/scripts/apply_best_params.py"
    )

    # DAGの流れ: 最適化 → MetaAI再学習 → 適用
    optimize_worker_1 >> apply_to_metaai >> apply_to_kingdom
