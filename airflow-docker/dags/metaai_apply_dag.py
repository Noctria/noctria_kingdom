from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

# ✅ DAG定義
with DAG(
    dag_id="metaai_apply_dag",
    schedule_interval=None,  # 手動トリガー or 他のDAGから連携
    start_date=days_ago(1),
    catchup=False,
    tags=["noctria", "metaai", "apply"]
) as dag:

    # ✅ 最適パラメータをMetaAIへ適用して再学習
    apply_metaai = BashOperator(
        task_id="apply_best_params_to_metaai",
        bash_command="python3 /opt/airflow/scripts/apply_best_params_to_metaai.py"
    )
