from core.path_config import CORE_DIR, DAGS_DIR, DATA_DIR, INSTITUTIONS_DIR, LOGS_DIR, MODELS_DIR, PLUGINS_DIR, SCRIPTS_DIR, STRATEGIES_DIR, TESTS_DIR, TOOLS_DIR, VERITAS_DIR
import sys
import os
import importlib.util
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

# ✅ Noctria Kingdom v2.0 パス管理構成
from core.path_config import LOGS_DIR, STRATEGIES_DIR
from core.logger import setup_logger
from core.noctria import Noctria

# ✅ PYTHONPATHをAirflow Workerで有効化（戦略読み込み用）

# === DAG共通設定 ===
default_args = {
    'owner': 'Noctria',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    dag_id='noctria_kingdom_dag',
    default_args=default_args,
    description='Noctria王国戦略統合DAG（official戦略を動的適用）',
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'kingdom', 'veritas']
)

# === ログファイル（v2.0構成に準拠）
log_file_path = LOGS_DIR / "noctria_decision.log"
logger = setup_logger("NoctriaDecision", str(log_file_path))

# === 戦略ディレクトリの取得（ハードコード撤廃）
OFFICIAL_DIR = STRATEGIES_DIR / "official"

# === 動的タスク生成関数 ===
def create_strategy_task(strategy_name, strategy_path):
    def strategy_callable(**kwargs):
        try:
            spec = importlib.util.spec_from_file_location(strategy_name, strategy_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if not hasattr(module, "simulate"):
                logger.warning(f"❌ {strategy_name} は simulate() を定義していません")
                return

            result = module.simulate()
            logger.info(f"[{strategy_name}] result: {result}")
            kwargs["ti"].xcom_push(key=f"{strategy_name}_decision", value=result)

        except Exception as e:
            logger.error(f"[{strategy_name}] 実行エラー: {e}")

    return strategy_callable

# === DAGタスク定義 ===
with dag:
    strategy_tasks = []
    for fname in os.listdir(OFFICIAL_DIR):
        if fname.endswith(".py"):
            strategy_name = os.path.splitext(fname)[0]
            strategy_path = str(OFFICIAL_DIR / fname)
            task = PythonOperator(
                task_id=f"{strategy_name}_strategy",
                python_callable=create_strategy_task(strategy_name, strategy_path)
            )
            strategy_tasks.append((strategy_name, task))

    # === Noctriaによる統合判断 ===
    def noctria_final_decision(**kwargs):
        ti = kwargs['ti']
        decisions = {}
        for strategy_name, _ in strategy_tasks:
            val = ti.xcom_pull(key=f"{strategy_name}_decision", task_ids=f"{strategy_name}_strategy")
            decisions[strategy_name] = val
        logger.info(f"👑 Noctriaが受け取った判断: {decisions}")
        noctria = Noctria()
        final_action = noctria.meta_ai.decide_final_action(decisions)
        logger.info(f"🏰 王国最終判断: {final_action}")

    final_task = PythonOperator(
        task_id="noctria_final_decision",
        python_callable=noctria_final_decision
    )

    for _, task in strategy_tasks:
        task >> final_task