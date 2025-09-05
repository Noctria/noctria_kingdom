# /opt/airflow/dags/simulate_strategy_dag.py

from datetime import datetime, timedelta
from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator

# ================================================
# ★ 修正: 新しいimportルールを適用
# ================================================
# `PYTHONPATH`が設定されたため、sys.pathハックは不要。
# 全てのモジュールは、srcを起点とした絶対パスでインポートする。
from core.path_config import LOGS_DIR
from core.logger import setup_logger

# ★ 改善点: 外部スクリプトを実行するのではなく、関数として直接インポートする
try:
    from execution.simulate_official_strategy import main as run_official_simulation
except ImportError:
    # ローカルでのテストなど、インポートに失敗した場合のダミー関数
    def run_official_simulation():
        print("警告: `simulate_official_strategy.main`が見つかりませんでした。ダミー処理を実行します。")
        pass

# ================================================
# 🏰 王国記録係（DAGロガー）の召喚
# ================================================
dag_log_path = LOGS_DIR / "dags" / "simulate_strategy_dag.log"
logger = setup_logger("SimulateStrategyDAG", dag_log_path)


# ================================================
# 📝 タスク定義
# ================================================
def simulation_task_wrapper():
    """
    インポートしたシミュレーション関数を実行するラッパー
    """
    logger.info("🚀 戦略バックテストを開始します...")
    try:
        run_official_simulation()
        logger.info("✅ シミュレーション完了")
    except Exception as e:
        logger.error(f"❌ シミュレーション失敗: {e}", exc_info=True)
        raise

# ================================================
# 📜 DAG設定
# ================================================
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
        python_callable=simulation_task_wrapper,
    )
