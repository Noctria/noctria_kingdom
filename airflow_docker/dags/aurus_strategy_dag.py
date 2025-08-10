# airflow_docker/dags/aurus_strategy_dag.py
# 変更点:
# ① Airflow 2.x の get_current_context() に移行（provide_context 廃止）
# ② 例外時含めてログ整備（logger使用）
# ③ pdca_events への簡易ロギングを追加（任意・安全に失敗無視）
# ④ XComのキー名は既存踏襲

from datetime import datetime, timedelta
import importlib
import logging

from airflow import DAG
from airflow.operators.python import PythonOperator, get_current_context

# 軽量ロギング（DBは失敗しても本処理は継続）
try:
    from src.core.db_logging import log_event as _db_log_event  # optional
except Exception:
    _db_log_event = None

logger = logging.getLogger("AurusStrategyDAG")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")

STRATEGY_MODULE = "strategies.aurus_singularis"
STRATEGY_CLASS = "AurusSingularis"
DAG_ID = "aurus_strategy_dag"
DESCRIPTION = "⚔️ Noctria Kingdomの戦術官Aurusによるトレンド解析DAG"

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
        # DBロギングは失敗しても落とさない
        logger.debug(f"pdca_events log skipped: {e}")

def trigger_task():
    reason = _reason_from_conf()
    logger.info(f"【Aurusトリガータスク・発令理由】{reason}")

    mock_market_data = {
        "price": 1.2345,
        "volume": 500,
        "sentiment": 0.7,
        "trend_strength": 0.5,
        "volatility": 0.12,
        "order_block": 0.3,
        "momentum": 0.8,
        "trend_prediction": "bullish",
        "liquidity_ratio": 1.1,
        "trigger_reason": reason,
    }

    _safe_db_log("AURUS_TRIGGERED", {"reason": reason, "sample_keys": list(mock_market_data.keys())})
    return mock_market_data  # XCom: return_value

def strategy_task():
    ctx = get_current_context()
    reason = _reason_from_conf()
    logger.info(f"【Aurus解析タスク・発令理由】{reason}")

    input_data = ctx["ti"].xcom_pull(task_ids="trigger_task")
    if not input_data:
        # フォールバック（最低限の構造）
        input_data = {k: 0.0 for k in [
            "price", "volume", "sentiment", "trend_strength", "volatility",
            "order_block", "momentum", "trend_prediction", "liquidity_ratio"
        ]}
        input_data["trigger_reason"] = reason

    try:
        strategy_module = importlib.import_module(STRATEGY_MODULE)
        StrategyClass = getattr(strategy_module, STRATEGY_CLASS)
        strategy = StrategyClass()

        decision = strategy.propose(input_data)
        result = {"decision": decision, "reason": reason}

        _safe_db_log("AURUS_DECIDED", {"reason": reason, "decision_head": str(decision)[:240]})
        logger.info(f"🔮 {STRATEGY_CLASS}の戦略判断: {result}")
        return result  # XCom: return_value
    except Exception as e:
        logger.error(f"❌ {STRATEGY_CLASS}戦略中にエラー発生: {e}", exc_info=True)
        _safe_db_log("AURUS_ERROR", {"reason": reason, "error": str(e)})
        # エラーでもDAG全体は継続させたい運用なら None を返す
        return None

with DAG(
    dag_id=DAG_ID,
    default_args=default_args,
    description=DESCRIPTION,
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=["noctria", "trend-analysis"],
) as dag:

    t1 = PythonOperator(
        task_id="trigger_task",
        python_callable=trigger_task,
    )

    t2 = PythonOperator(
        task_id="strategy_analysis_task",
        python_callable=strategy_task,
    )

    t1 >> t2
