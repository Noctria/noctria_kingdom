from core.path_config import CORE_DIR, DAGS_DIR, DATA_DIR, INSTITUTIONS_DIR, LOGS_DIR, MODELS_DIR, PLUGINS_DIR, SCRIPTS_DIR, STRATEGIES_DIR, TESTS_DIR, TOOLS_DIR, VERITAS_DIR
import sys
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

# ✅ パス集中管理（Noctria Kingdom v2.0 構成）
from core.path_config import SCRIPTS_DIR

# ✅ Python モジュール参照用に scripts ディレクトリを明示追加

# ✅ 外部スクリプトの関数をインポート（PDCA構成）
from optimize_params_with_optuna import optimize_main
from apply_best_params_to_metaai import apply_best_params_to_metaai
from apply_best_params import apply_best_params_to_kingdom

# ✅ DAG 共通設定
default_args = {
    "owner": "Noctria",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# ✅ DAG 定義（Airflowは王の伝令役）
with DAG(
    dag_id="noctria_kingdom_pdca_dag",
    description="🏰 Noctria KingdomのPDCAサイクル統合DAG（Optuna最適化 → MetaAI再学習 → 戦略適用）",
    default_args=default_args,
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=["noctria", "kingdom", "pdca"],
) as dag:

    # 🔍 Step 1: 戦略の試練（Optuna最適化）
    optimize_task = PythonOperator(
        task_id="optimize_worker_1",
        python_callable=optimize_main,
    )

    # 📘 Step 2: MetaAIへの叡智の継承（最適パラメータ再学習）
    apply_metaai_task = PythonOperator(
        task_id="apply_best_params_to_metaai",
        python_callable=apply_best_params_to_metaai,
    )

    # 🏁 Step 3: 王国の未来を定める（戦略反映）
    apply_kingdom_task = PythonOperator(
        task_id="apply_best_params_to_kingdom",
        python_callable=apply_best_params_to_kingdom,
    )

    # ✅ DAGフロー構築（指令系統）
    optimize_task >> apply_metaai_task >> apply_kingdom_task