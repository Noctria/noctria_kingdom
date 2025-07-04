from core.path_config import CORE_DIR, DAGS_DIR, DATA_DIR, INSTITUTIONS_DIR, LOGS_DIR, MODELS_DIR, PLUGINS_DIR, SCRIPTS_DIR, STRATEGIES_DIR, TESTS_DIR, TOOLS_DIR, VERITAS_DIR
import sys
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

# ✅ パス管理構成に準拠
from core.path_config import SCRIPTS_DIR

# ✅ コンテナ用PYTHONPATH

# ✅ 外部スクリプト読み込み
from evaluate_metaai_model import evaluate_metaai_model

# ✅ DAG定義
with DAG(
    dag_id="metaai_evaluate_dag",
    schedule_interval=None,
    start_date=days_ago(1),
    catchup=False,
    tags=["noctria", "metaai", "evaluate"],
    description="📊 MetaAIの最新モデルを評価し、戦略の有効性を測定するDAG",
) as dag:

    evaluate_task = PythonOperator(
        task_id="evaluate_metaai_model",
        python_callable=evaluate_metaai_model,
    )