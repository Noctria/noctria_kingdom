from core.path_config import CORE_DIR, DAGS_DIR, DATA_DIR, INSTITUTIONS_DIR, LOGS_DIR, MODELS_DIR, PLUGINS_DIR, SCRIPTS_DIR, STRATEGIES_DIR, TESTS_DIR, TOOLS_DIR, VERITAS_DIR
import sys
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

# ✅ Noctria Kingdom パス管理（v2.0）
from core.path_config import SCRIPTS_DIR

# ✅ Docker・Airflow環境対応：スクリプトディレクトリを明示追加

# ✅ 外部スクリプト：MetaAIへの最適パラメータ適用ロジック
from scripts.apply_best_params_to_metaai import apply_best_params_to_metaai

# ✅ DAG構成：MetaAIへの単体適用用DAG
with DAG(
    dag_id="metaai_apply_dag",
    schedule_interval=None,  # GUI or 他DAGからのトリガー前提
    start_date=days_ago(1),
    catchup=False,
    tags=["noctria", "metaai", "retrain"],
    description="📌 MetaAIに最適パラメータを適用する単体DAG",
) as dag:

    apply_metaai_task = PythonOperator(
        task_id="apply_best_params_to_metaai",
        python_callable=apply_best_params_to_metaai,
    )