# airflow_docker/dags/hermes_strategy_dag.py
# 変更点:
# ① Airflow 2.x の get_current_context() を使用（provide_context 廃止）
# ② XComは return_value で受け渡しに統一
# ③ pdca_events への簡易ロギングを追加（失敗しても無視）
# ④ 例外ログ整備

from datetime import datetime, timedelta
import importlib
import logging

from airflow import DAG
from airflow.operators.python import PythonOperator, get_current_context

# optional: DBロギング（失敗しても本処理は継続）
try:
    from src.core.db_logging import log_event as _db_log_event
except Exception:
    _db_log_event = None

logger = logging.getLogger("HermesStrategyDAG")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")

STRATEGY_MODULE = "strategies.hermes_cognitor"
STRATEGY_CLASS = "HermesCognitorStrategy"
DAG_ID = "hermes_strategy_dag"
DESCRIPTION = "🦉 Noctria Kingdomの言語大臣Hermes Cognitorによる説明生成DAG"

default_args = {
    "owner": "Noctria",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

def _reason_from_conf() -> str:
    ctx = get_current_context()
    dr = ctx.get("dag_run")
    return (dr.conf or {}).get("reason", "理由未指定") if dr else "理由未指定"

def _safe_db_log(event_type: str, payload: dict):
    if _db_log_event is None:
        return
    try:
        _db_log_event(
            table="pdca_events",
            event_type=event_type,
            payload=payload,
            occurred_at=datetime.utcnow(),
        )
    except Exception as e:
        logger.debug(f"pdca_events log skipped: {e}")

def trigger_task():
    reason = _reason_from_conf()
    logger.info(f"【Hermesトリガータスク・発令理由】{reason}")

    # 説明生成の元ネタ（ダミー）
    mock_features = {
        "win_rate": 75.2,
        "max_drawdown": -4.1,
        "news_count": 18,
        "fomc_today": True,
        "risk": "low",
    }
    mock_labels = [
        "勝率が良好です",
        "リスク水準が低下しています",
        "今日はFOMCイベント日です",
    ]

    _safe_db_log("HERMES_TRIGGERED", {"reason": reason, "feature_keys": list(mock_features.keys())})
    # XCom: return_value で次タスクへ
    return {"features": mock_features, "labels": mock_labels, "reason": reason}

def hermes_strategy_task():
    ctx = get_current_context()
    reason = _reason_from_conf()
    logger.info(f"【Hermes解析タスク・発令理由】{reason}")

    payload = ctx["ti"].xcom_pull(task_ids="trigger_task") or {}
    features = payload.get("features", {})
    labels = payload.get("labels", [])

    try:
        strategy_module = importlib.import_module(STRATEGY_MODULE)
        StrategyClass = getattr(strategy_module, STRATEGY_CLASS)
        strategy = StrategyClass()

        explanation = strategy.summarize_strategy(features, labels)
        result = {"explanation": explanation, "reason": reason}

        _safe_db_log("HERMES_EXPLAINED", {"reason": reason, "explanation_head": str(explanation)[:240]})
        logger.info(f"🦉 Hermesの説明生成結果: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ {STRATEGY_CLASS}実行中にエラー発生: {e}", exc_info=True)
        _safe_db_log("HERMES_ERROR", {"reason": reason, "error": str(e)})
        return None

with DAG(
    dag_id=DAG_ID,
    default_args=default_args,
    description=DESCRIPTION,
    schedule_interval=None,  # 必要に応じて「@daily」等に変更
    start_date=datetime(2025, 7, 21),
    catchup=False,
    tags=["noctria", "llm", "explanation"],
) as dag:

    t1 = PythonOperator(
        task_id="trigger_task",
        python_callable=trigger_task,
    )

    t2 = PythonOperator(
        task_id="hermes_strategy_task",
        python_callable=hermes_strategy_task,
    )

    t1 >> t2
