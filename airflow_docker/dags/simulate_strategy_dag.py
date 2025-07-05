# /opt/airflow/airflow_docker/dags/simulate_strategy_dag.py

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

import sys
from pathlib import Path
sys.path.append("/opt/airflow")

from core.path_config import PROJECT_ROOT
from core.logger import setup_logger

logger = setup_logger("SimulateStrategy")

# ✅ 外部スクリプトの読み込み
SIMULATE_SCRIPT = PROJECT_ROOT / "execution" / "simulate_official_strategy.py"

def run_simulation():
    logger.info("🚀 戦略バックテストを開始します...")
    try:
        exec_globals = {}
        with open(SIMULATE_SCRIPT, "r", encoding="utf-8") as f:
            code = f.read()
            exec(code, exec_globals)
        exec_globals["simulate_official_strategy"]()
        logger.info("✅ シミュレーション完了")
    except Exception as e:
        logger.error(f"❌ シミュレーション失敗: {e}")
        raise

# === DAG設定 ===
default_args = {
    "owner": "Noctria",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    dag_id="simulate_strategy_dag",
    default_args=default_args,
    description="📊 昇格済み戦略モデルのシミュレーションDAG",
    schedule_interval=None,
    start_date=datetime(2025, 7, 1),
    catchup=False,
    tags=["metaai", "simulation", "noctria"],
)

run_task = PythonOperator(
    task_id="simulate_official_strategy",
    python_callable=run_simulation,
    dag=dag,
)
