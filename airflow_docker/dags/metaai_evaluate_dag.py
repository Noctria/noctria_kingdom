raise ImportError("metaai_evaluate_dag is temporarily disabled: MODELS_DIR was removed in path_config.")
from core.path_config import CORE_DIR, DAGS_DIR, DATA_DIR, INSTITUTIONS_DIR, LOGS_DIR, MODELS_DIR, PLUGINS_DIR, SCRIPTS_DIR, STRATEGIES_DIR, TESTS_DIR, TOOLS_DIR, VERITAS_DIR
import sys
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

from src.core.path_config import DATA_DIR, LOGS_DIR, STRATEGIES_VERITAS_GENERATED_DIR, VERITAS_EVAL_LOG

from scripts.evaluate_metaai_model import evaluate_metaai_model

def evaluate_metaai_task(**kwargs):
    # confから理由受信
    conf = kwargs.get("dag_run").conf if kwargs.get("dag_run") else {}
    reason = conf.get("reason", "理由未指定")
    print(f"【MetaAI評価タスク・発令理由】{reason}")

    # 実際の評価タスク実行
    result = evaluate_metaai_model()
    # 理由付きでXComに記録
    ti = kwargs["ti"]
    ti.xcom_push(key="evaluation_result", value={"result": result, "trigger_reason": reason})
    return result

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
        python_callable=evaluate_metaai_task,
        provide_context=True,
    )
