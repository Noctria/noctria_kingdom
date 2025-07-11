# /opt/airflow/dags/simulate_strategy_dag.py

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

import sys
from pathlib import Path

# Airflowコンテナ内のルートパスを追加して、coreなどをインポート可能にする
sys.path.append("/opt/airflow")

# ★ 修正点 1: LOGS_DIRもインポートする
from core.path_config import PROJECT_ROOT, LOGS_DIR
from core.logger import setup_logger

# ★ 修正点 2: このDAG専用のログファイルパスを定義し、引数として渡す
dag_log_path = LOGS_DIR / "dags" / "simulate_strategy_dag.log"
logger = setup_logger("SimulateStrategyDAG", dag_log_path)

# ✅ 外部スクリプトの読み込み
SIMULATE_SCRIPT = PROJECT_ROOT / "execution" / "simulate_official_strategy.py"

def run_simulation():
    """外部のシミュレーションスクリプトを実行する"""
    logger.info("🚀 戦略バックテストを開始します...")
    try:
        # スクリプトを読み込んで実行
        exec_globals = {}
        with open(SIMULATE_SCRIPT, "r", encoding="utf-8") as f:
            code = f.read()
            exec(code, exec_globals)
        
        # スクリプト内で定義されているはずのメイン関数を呼び出す
        exec_globals["simulate_official_strategy"]()
        logger.info("✅ シミュレーション完了")
        
    except Exception as e:
        logger.error(f"❌ シミュレーション失敗: {e}", exc_info=True)
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

with DAG(
    dag_id="simulate_strategy_dag",
    default_args=default_args,
    description="📊 昇格済み戦略モデルのシミュレーションDAG",
    schedule_interval=None,
    start_date=datetime(2025, 7, 1),
    catchup=False,
    tags=["metaai", "simulation", "noctria"],
) as dag:

    run_task = PythonOperator(
        task_id="simulate_official_strategy",
        python_callable=run_simulation,
    )
