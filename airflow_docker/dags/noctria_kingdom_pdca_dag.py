# airflow_docker/dags/noctria_kingdom_pdca_dag.py

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

# ================================
# 🛣️ パス調整（scriptsをimport可能に）
# ================================
from core.path_config import SCRIPTS_DIR
import sys
sys.path.append(str(SCRIPTS_DIR))

# ================================
# 🏰 勅令: 外部戦略スクリプトの召喚
# ================================
from optimize_params_with_optuna import optimize_main
from apply_best_params_to_metaai import apply_best_params_to_metaai
from apply_best_params_to_kingdom import apply_best_params_to_kingdom

# ================================
# 📜 王命: DAG共通設定
# ================================
default_args = {
    "owner": "Noctria",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# ================================
# 👑 王命: Noctria Kingdom 統合PDCAサイクル
# ================================
with DAG(
    dag_id="noctria_kingdom_pdca_dag",
    description="🏰 Noctria KingdomのPDCAサイクル統合DAG（Optuna最適化 → MetaAI再学習 → 王国戦略反映）",
    default_args=default_args,
    schedule_interval=None,  # 手動実行想定
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=["noctria", "kingdom", "pdca", "metaai"],
) as dag:

    # 🎯 第壱試練：叡智の探求（Optunaによる最適化）
    optimize_task = PythonOperator(
        task_id="optimize_with_optuna",
        python_callable=optimize_main,
    )

    # 🧠 第弐試練：MetaAIへの叡智継承（最適戦略で再学習）
    apply_metaai_task = PythonOperator(
        task_id="apply_best_params_to_metaai",
        python_callable=apply_best_params_to_metaai,
    )

    # ⚔️ 第参試練：王国戦略の制定（正式昇格）
    apply_kingdom_task = PythonOperator(
        task_id="apply_best_params_to_kingdom",
        python_callable=apply_best_params_to_kingdom,
    )

    # 🔗 王命の流れ：叡智 → 習得 → 王政制定
    optimize_task >> apply_metaai_task >> apply_kingdom_task
