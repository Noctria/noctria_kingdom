# dags/metaai_apply_dag.py

from datetime import datetime
from typing import Dict, Any
from airflow.decorators import dag, task
from airflow.operators.python import get_current_context


from core.path_config import LOGS_DIR
from core.logger import setup_logger
from scripts.apply_best_params_to_metaai import apply_best_params_to_metaai

dag_log_path = LOGS_DIR / "dags" / "metaai_apply_dag.log"
logger = setup_logger("MetaAIApplyDAG", dag_log_path)

@dag(
    dag_id="metaai_apply_dag",
    schedule=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=["noctria", "metaai", "retrain", "apply"],
    description="📌 MetaAIに指定された最適パラメータを適用し、再学習・評価・保存する単体DAG",
    params={
        "best_params": {}
    }
)
def metaai_apply_pipeline():
    """
    指定されたパラメータでMetaAIモデルを再学習し、
    バージョン管理されたモデルとして保存するパイプライン。
    conf（理由等）も全タスクで受信・記録可能
    """

    @task
    def apply_task(params: Any) -> Dict:
        from airflow.decorators import get_current_context
        ctx = get_current_context()
        conf = ctx["dag_run"].conf if ctx.get("dag_run") and ctx["dag_run"].conf else {}
        reason = conf.get("reason", "理由未指定")

        best_params = params.get("best_params")
        if not best_params:
            logger.error("❌ 実行パラメータ 'best_params' が指定されていません。")
            raise ValueError("Configuration 'best_params' is required to run this DAG.")

        logger.info(f"【MetaAI Applyタスク・発令理由】{reason}")
        logger.info(f"🧠 MetaAIへの叡智継承を開始します (パラメータ: {best_params})")

        model_info = apply_best_params_to_metaai(best_params=best_params)
        # 理由も返却データに含めてXComへ
        result = {
            "model_info": model_info,
            "trigger_reason": reason
        }
        logger.info(f"✅ MetaAIへの継承が完了しました: {result}")
        return result

    apply_task(params="{{ params }}")

metaai_apply_pipeline()
