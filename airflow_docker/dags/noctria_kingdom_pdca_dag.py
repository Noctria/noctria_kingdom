# airflow_docker/dags/noctria_kingdom_pdca_dag.py
# 変更点:
# ① sys.pathハック削除
# ② importを src. プレフィックスへ
# ③ get_current_context() 使用（operators.python から）
# ④ provide_context削除
# ⑤ conf/paramsの参照整理
# ⑥ 各主要タスク終了時に log_event() でDBロギング追加

from datetime import datetime, timedelta
import logging

from airflow.models.dag import DAG
from airflow.operators.python import get_current_context
from src.core.path_config import LOGS_DIR
from src.core.logger import setup_logger
from src.core.db_logging import log_event
from src.scripts.optimize_params_with_optuna import optimize_main
from src.scripts.apply_best_params_to_metaai import apply_best_params_to_metaai
from src.scripts.apply_best_params_to_kingdom import apply_best_params_to_kingdom

dag_log_path = LOGS_DIR / "dags" / "noctria_kingdom_pdca_dag.log"
logger = setup_logger("NoctriaPDCA_DAG", dag_log_path)


def task_failure_alert(context):
    # 必要なら失敗通知実装
    pass


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

        log_event(
            table="pdca_events",
            event_type="OPTIMIZE_COMPLETED",
            payload={"worker_id": worker_id, "best_params": best_params, "reason": _conf_reason()}
        )
        return best_params

    def select_best_params_task(**_):
        ctx = get_current_context()
        ti = ctx["ti"]
        worker_count = ctx["params"].get("worker_count", 3)
        logger.info(f"【選定理由】{_conf_reason()}")
        results = [ti.xcom_pull(task_ids=f"optimize_worker_{i}") for i in range(1, worker_count + 1)]
        results = [r for r in results if r]

        if not results:
            logger.warning("全ワーカー結果が空")
            return None

        best = max(results, key=lambda p: p.get("score", 0))
        ti.xcom_push(key="best_params", value=best)

        log_event(
            table="pdca_events",
            event_type="BEST_PARAMS_SELECTED",
            payload={"best_params": best, "reason": _conf_reason()}
        )
        return best

    def apply_metaai_task(**_):
        ctx = get_current_context()
        best_params = ctx["ti"].xcom_pull(key="best_params", task_ids="select_best_params")
        logger.info(f"【MetaAI適用理由】{_conf_reason()}")

        if not best_params:
            logger.warning("ベストパラメータなし")
            return None

        result = apply_best_params_to_metaai(best_params=best_params)

        log_event(
            table="pdca_events",
            event_type="META_AI_APPLIED",
            payload={"best_params": best_params, "result": result, "reason": _conf_reason()}
        )
        return result

    def apply_kingdom_task(**_):
        ctx = get_current_context()
        model_info = ctx["ti"].xcom_pull(task_ids="apply_best_params_to_metaai")
        logger.info(f"【Kingdom昇格理由】{_conf_reason()}")

        if not model_info:
            logger.warning("モデル情報なし")
            return None

        result = apply_best_params_to_kingdom(model_info=model_info)

        log_event(
            table="pdca_events",
            event_type="KINGDOM_PROMOTED",
            payload={"model_info": model_info, "result": result, "reason": _conf_reason()}
        )
        return result

    def royal_decision_task(**_):
        logger.info(f"【王決断理由】{_conf_reason()}")
        from src.noctria_ai.noctria import Noctria
        try:
            result = Noctria().execute_trade()
            log_event(
                table="pdca_events",
                event_type="ROYAL_DECISION",
                payload={"result": result, "reason": _conf_reason()}
            )
            return result
        except Exception as e:
            logger.error(f"王決断で例外: {e}")
            log_event(
                table="pdca_events",
                event_type="ROYAL_DECISION_ERROR",
                payload={"error": str(e), "reason": _conf_reason()}
            )
            return {"status": "error", "message": str(e)}

    workers = [
        PythonOperator(
            task_id=f"optimize_worker_{i}",
            python_callable=optimize_worker_task,
            op_kwargs={"worker_id": i}
        )
        for i in range(1, dag.params["worker_count"] + 1)
    ]

    select_best = PythonOperator(task_id="select_best_params", python_callable=select_best_params_task)
    apply_metaai = PythonOperator(task_id="apply_best_params_to_metaai", python_callable=apply_metaai_task)
    apply_kingdom = PythonOperator(task_id="apply_best_params_to_kingdom", python_callable=apply_kingdom_task)
    royal_decision = PythonOperator(task_id="royal_decision", python_callable=royal_decision_task)

    workers >> select_best >> apply_metaai >> apply_kingdom >> royal_decision
