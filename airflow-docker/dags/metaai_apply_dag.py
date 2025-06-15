from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

# === DAG定義 ===
with DAG(
    dag_id="metaai_apply_dag",
    description="🤖 Noctria Kingdomの知性核MetaAIへの再学習適用DAG",
    schedule_interval=None,  # 手動 or 他DAG連携による発火
    start_date=days_ago(1),
    catchup=False,
    tags=["noctria", "metaai", "apply"]
) as dag:

    # 👑 王Noctriaの命により、MetaAIへ最適パラメータを適用し再学習を行う
    apply_metaai = BashOperator(
        task_id="apply_best_params_to_metaai",
        bash_command="python3 /opt/airflow/scripts/apply_best_params_to_metaai.py"
    )
