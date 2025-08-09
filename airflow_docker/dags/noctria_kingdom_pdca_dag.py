# 変更点: ① sys.pathハック削除 ② importを src. プレフィックスへ
#        ③ get_current_context() ④ provide_context削除 ⑤ conf/paramsの参照整理
from datetime import datetime, timedelta
import logging

from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.context import get_current_context

from src.core.path_config import LOGS_DIR
from src.core.logger import setup_logger
from src.scripts.optimize_params_with_optuna import optimize_main
from src.scripts.apply_best_params_to_metaai import apply_best_params_to_metaai
from src.scripts.apply_best_params_to_kingdom import apply_best_params_to_kingdom

dag_log_path = LOGS_DIR / "dags" / "noctria_kingdom_pdca_dag.log"
logger = setup_logger("NoctriaPDCA_DAG", dag_log_path)

def task_failure_alert(context):
    ...

default_args = {
    "owner": "Noctria",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "on_failure_callback": task_failure_alert,
}

with DAG(
    dag_id="noctria_kingdom_pdca_dag",
    description="Optuna→MetaAI→Kingdom→Royal Decision のPDCA統合",
    schedule_interval="@daily",
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=["noctria", "kingdom", "pdca", "metaai", "royal"],
    params={"worker_count": 3, "n_trials": 100},
) as dag:

    def _conf_reason():
        ctx = get_current_context()
        dr = ctx.get("dag_run")
        return (dr.conf or {}).get("reason", "理由未指定") if dr else "理由未指定"

    def optimize_worker_task(worker_id: int, **_):
        logger.info(f"【実行理由】worker_{worker_id}: {_conf_reason()}")
        n_trials = get_current_context()["params"].get("n_trials", 100)
        best_params = optimize_main(n_trials=n_trials)
        if not best_params:
            logger.warning(f"worker_{worker_id}: ベストなし")
            return None
        return best_params

    def select_best_params_task(**_):
        ctx = get_current_context()
        ti = ctx["ti"]
        worker_count = ctx["params"].get("worker_count", 3)
        logger.info(f"【選定理由】{_conf_reason()}")
        results = [ti.xcom_pull(task_ids=f"optimize_worker_{i}") for i in range(1, worker_count+1)]
        results = [r for r in results if r]
        if not results:
            logger.warning("全ワーカー結果が空")
            return None
        best = max(results, key=lambda p: p.get("score", 0))
        ti.xcom_push(key="best_params", value=best)
        return best

    def apply_metaai_task(**_):
        ctx = get_current_context()
        best_params = ctx["ti"].xcom_pull(key="best_params", task_ids="select_best_params")
        logger.info(f"【MetaAI適用理由】{_conf_reason()}")
        if not best_params:
            logger.warning("ベストパラメータなし")
            return None
        return apply_best_params_to_metaai(best_params=best_params)

    def apply_kingdom_task(**_):
        ctx = get_current_context()
        model_info = ctx["ti"].xcom_pull(task_ids="apply_best_params_to_metaai")
        logger.info(f"【Kingdom昇格理由】{_conf_reason()}")
        if not model_info:
            logger.warning("モデル情報なし")
            return None
        return apply_best_params_to_kingdom(model_info=model_info)

    def royal_decision_task(**_):
        logger.info(f"【王決断理由】{_conf_reason()}")
        from src.noctria_ai.noctria import Noctria  # 明示的に src. へ
        try:
            return Noctria().execute_trade()
        except Exception as e:
            logger.error(f"王決断で例外: {e}")
            return {"status": "error", "message": str(e)}

    workers = [
        PythonOperator(task_id=f"optimize_worker_{i}",
                       python_callable=optimize_worker_task,
                       op_kwargs={"worker_id": i})
        for i in range(1, dag.params["worker_count"] + 1)
    ]
    select_best = PythonOperator(task_id="select_best_params", python_callable=select_best_params_task)
    apply_metaai = PythonOperator(task_id="apply_best_params_to_metaai", python_callable=apply_metaai_task)
    apply_kingdom = PythonOperator(task_id="apply_best_params_to_kingdom", python_callable=apply_kingdom_task)
    royal_decision = PythonOperator(task_id="royal_decision", python_callable=royal_decision_task)

    workers >> select_best >> apply_metaai >> apply_kingdom >> royal_decision
