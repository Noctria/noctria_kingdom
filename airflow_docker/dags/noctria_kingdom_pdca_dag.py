from core.path_config import CORE_DIR, DAGS_DIR, DATA_DIR, INSTITUTIONS_DIR, LOGS_DIR, MODELS_DIR, PLUGINS_DIR, SCRIPTS_DIR, STRATEGIES_DIR, TESTS_DIR, TOOLS_DIR, VERITAS_DIR
import sys
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

# 📜 勅令: パスの統治を一元化（Noctria Kingdom v2.0 構成）
from core.path_config import SCRIPTS_DIR

# 🛡️ 勅令: 外部スクリプトの戦略知識を王国へ導入
from scripts.optimize_params_with_optuna import optimize_main
from scripts.apply_best_params_to_metaai import apply_best_params_to_metaai
from scripts.apply_best_params_to_kingdom import apply_best_params_to_kingdom

# 🏰 王国のDAG共通設定（伝令たちの心得）
default_args = {
    "owner": "Noctria",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# 👑 王Noctriaの命令書（DAGの定義）
with DAG(
    dag_id="noctria_kingdom_pdca_dag",
    description="🏰 Noctria KingdomのPDCAサイクル統合DAG（Optuna最適化 → MetaAI再学習 → 王国戦略反映）",
    default_args=default_args,
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=["noctria", "kingdom", "pdca"],
) as dag:

    # 🎯 第壱試練：叡智の探求（Optunaによる最適化の儀）
    optimize_task = PythonOperator(
        task_id="optimize_worker_1",
        python_callable=optimize_main,
    )

    # 🧠 第弐試練：MetaAIへの叡智継承（最適戦略の習得）
    apply_metaai_task = PythonOperator(
        task_id="apply_best_params_to_metaai",
        python_callable=apply_best_params_to_metaai,
    )

    # ⚔️ 第参試練：王国戦略の制定（叡智を王国に反映）
    apply_kingdom_task = PythonOperator(
        task_id="apply_best_params_to_kingdom",
        python_callable=apply_best_params_to_kingdom,
    )

    # 🔗 勅令系統：王命は流れの如く、段階を経て施行される
    optimize_task >> apply_metaai_task >> apply_kingdom_task
