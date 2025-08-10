# airflow_docker/dags/noctria_kingdom_pdca_dag.py
# 変更点（Pattern A 版）:
# - optimize_main を PythonOperator から直接呼び出し
# - provide_context=True で context を渡す
# - 最適化完了ログは on_success_callback で記録
# - schedule_interval → schedule
# - best選定は minimize に応じて min/max 切替
# - sys.path ハックなし、import は src. プレフィックス

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import logging

from airflow.models.dag import DAG
try:
    from airflow.operators.python import PythonOperator, get_current_context
except Exception:
    from airflow.operators.python_operator import PythonOperator  # type: ignore
    from airflow.operators.python_operator import get_current_context  # type: ignore

from src.core.path_config import LOGS_DIR
from src.core.logger import setup_logger
from src.core.db_logging import log_event
from src.scripts.optimize_params_with_optuna import optimize_main
from src.scripts.apply_best_params_to_metaai import apply_best_params_to_metaai
from src.scripts.apply_best_params_to_kingdom import apply_best_params_to_kingdom

dag_log_path = LOGS_DIR / "dags" / "noctria_kingdom_pdca_dag.log"
logger = setup_logger("NoctriaPDCA_DAG", dag_log_path)

def task_failure_alert(context):
    # 必要に応じて Slack / メール等を実装
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
    schedule="@daily",
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=["noctria", "kingdom", "pdca", "metaai", "royal"],
    params={"worker_count": 3, "n_trials": 100},
) as dag:

    _DEFAULT_WORKER_COUNT = int(dag.params.get("worker_count", 3))

    def _conf_reason() -> str:
        ctx = get_current_context()
        dr = ctx.get("dag_run")
        if not dr:
            return "理由未指定"
        conf = dr.conf or {}
        return conf.get("reason", "理由未指定")

    # --- 最適化完了ログ (Pattern A 用) ---
    def _log_optimize_completed(context):
        ti = context["ti"]
        res = ti.xcom_pull(task_ids=context["task"].task_id)
        if not res:
            return
        try:
            log_event(
                table="pdca_events",
                event_type="OPTIMIZE_COMPLETED",
                payload={
                    "worker_id": context["task"].task_id,
                    "reason": (context.get("dag_run").conf or {}).get("reason", "理由未指定")
                              if context.get("dag_run") else "理由未指定",
                    "result": {
                        "study_name": res.get("study_name"),
                        "best_value": res.get("best_value"),
                        "best_params": res.get("best_params"),
                        "n_trials": res.get("n_trials"),
                        "worker_tag": res.get("worker_tag"),
                    },
                },
            )
        except Exception as e:
            logger.warning(f"log_event 失敗（OPTIMIZE_COMPLETED）: {e}")

    # --- ベスト選定 ---
    def select_best_params_task(**kwargs):
        ctx = get_current_context()
        ti = ctx["ti"]

        conf_wc = int((ctx.get("dag_run").conf or {}).get("worker_count", _DEFAULT_WORKER_COUNT)) \
            if ctx.get("dag_run") else _DEFAULT_WORKER_COUNT
        use_wc = min(conf_wc, _DEFAULT_WORKER_COUNT)
        logger.info(f"【選定理由】{_conf_reason()} / use_workers={use_wc}")

        results: List[Optional[Dict[str, Any]]] = [
            ti.xcom_pull(task_ids=f"optimize_worker_{i}") for i in range(1, use_wc + 1)
        ]
        results = [r for r in results if r and "best_value" in r and "best_params" in r]

        if not results:
            logger.warning("全ワーカー結果が空")
            return None

        params = (ctx.get("dag_run").conf or {}) if ctx.get("dag_run") else (ctx.get("params") or {})
        minimize = bool(str(params.get("minimize", "false")).lower() in ("1", "true", "yes"))

        keyfunc = (lambda r: r.get("best_value", float("inf"))) if minimize \
            else (lambda r: r.get("best_value", float("-inf")))
        best = min(results, key=keyfunc) if minimize else max(results, key=keyfunc)

        ti.xcom_push(key="best_params", value=best.get("best_params"))
        ti.xcom_push(key="best_result", value=best)

        try:
            log_event(
                table="pdca_events",
                event_type="BEST_PARAMS_SELECTED",
                payload={"best_result": best, "reason": _conf_reason()},
            )
        except Exception as e:
            logger.warning(f"log_event 失敗（BEST_PARAMS_SELECTED）: {e}")

        return best

    # --- MetaAI 反映 ---
    def apply_metaai_task(**kwargs):
        ctx = get_current_context()
        ti = ctx["ti"]
        best_params = ti.xcom_pull(key="best_params", task_ids="select_best_params")
        logger.info(f"【MetaAI適用理由】{_conf_reason()}")

        if not best_params:
            logger.warning("ベストパラメータなし")
            return None

        result = apply_best_params_to_metaai(best_params=best_params)

        try:
            log_event(
                table="pdca_events",
                event_type="META_AI_APPLIED",
                payload={"best_params": best_params, "result": result, "reason": _conf_reason()},
            )
        except Exception as e:
            logger.warning(f"log_event 失敗（META_AI_APPLIED）: {e}")

        return result

    # --- Kingdom 昇格 ---
    def apply_kingdom_task(**kwargs):
        ctx = get_current_context()
        model_info = ctx["ti"].xcom_pull(task_ids="apply_best_params_to_metaai")
        logger.info(f"【Kingdom昇格理由】{_conf_reason()}")

        if not model_info:
            logger.warning("モデル情報なし")
            return None

        result = apply_best_params_to_kingdom(model_info=model_info)

        try:
            log_event(
                table="pdca_events",
                event_type="KINGDOM_PROMOTED",
                payload={"model_info": model_info, "result": result, "reason": _conf_reason()},
            )
        except Exception as e:
            logger.warning(f"log_event 失敗（KINGDOM_PROMOTED）: {e}")

        return result

    # --- 王の決断 ---
    def royal_decision_task(**kwargs):
        logger.info(f"【王決断理由】{_conf_reason()}")
        from src.noctria_ai.noctria import Noctria
        try:
            result = Noctria().execute_trade()
            try:
                log_event(
                    table="pdca_events",
                    event_type="ROYAL_DECISION",
                    payload={"result": result, "reason": _conf_reason()},
                )
            except Exception as e:
                logger.warning(f"log_event 失敗（ROYAL_DECISION）: {e}")
            return result
        except Exception as e:
            logger.error(f"王決断で例外: {e}")
            try:
                log_event(
                    table="pdca_events",
                    event_type="ROYAL_DECISION_ERROR",
                    payload={"error": str(e), "reason": _conf_reason()},
                )
            except Exception as e2:
                logger.warning(f"log_event 失敗（ROYAL_DECISION_ERROR）: {e2}")
            return {"status": "error", "message": str(e)}

    # --- 共通パラメータ（Pattern A 用） ---
    common_params = {
        "study_name": "noctria_rl_ppo_fx",
        "env_id": "YourCustomTradingEnv-v0",
        "n_trials": 50,
        "max_train_steps": 120_000,
        "n_eval_episodes": 8,
        "sampler": "tpe",
        "pruner": "median",
        "allow_prune_after": 2000,
        "tb_logdir": "/opt/airflow/logs/tb/optuna_ppo",
        # minimize / reward_clip などは conf で上書き可
    }

    # --- Workers（optimize_main を直接呼ぶ：Pattern A） ---
    workers = [
        PythonOperator(
            task_id=f"optimize_worker_{i}",
            python_callable=optimize_main,    # ← 直接呼ぶ
            provide_context=True,             # ← 重要（context を渡す）
            params=common_params | {"seed": 40 + i},  # 各ワーカーでseed差別化
            on_success_callback=_log_optimize_completed,
        )
        for i in range(1, _DEFAULT_WORKER_COUNT + 1)
    ]

    select_best = PythonOperator(
        task_id="select_best_params",
        python_callable=select_best_params_task,
    )
    apply_metaai = PythonOperator(
        task_id="apply_best_params_to_metaai",
        python_callable=apply_metaai_task,
    )
    apply_kingdom = PythonOperator(
        task_id="apply_best_params_to_kingdom",
        python_callable=apply_kingdom_task,
    )
    royal_decision = PythonOperator(
        task_id="royal_decision",
        python_callable=royal_decision_task,
    )

    workers >> select_best >> apply_metaai >> apply_kingdom >> royal_decision
