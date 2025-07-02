import sys
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

# ✅ パス集中管理（v2.0設計原則）
from core.path_config import SCRIPTS_DIR

# ✅ Python import path に scripts ディレクトリを追加
sys.path.append(str(SCRIPTS_DIR))

# ✅ 外部スクリプトの関数をインポート
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

# ✅ DAG 定義
with DAG(
    dag_id="noctria_kingdom_pdca_dag",
    description="🏰 Noctria KingdomのPDCAサイクル統合DAG（Optuna最適化 → MetaAI再学習 → 戦略適用）",
    default_args=default_args,
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=["noctria", "kingdom", "pdca"],
) as dag:

    # 🔍 Step 1: Optunaによる戦略最適化
    optimize_worker_1 = PythonOperator(
        task_id="optimize_worker_1",
        python_callable=optimize_main,
    )

    # 📘 Step 2: best_params.jsonをMetaAIに適用して再学習
    apply_to_metaai = PythonOperator(
        task_id="apply_best_params_to_metaai",
        python_callable=apply_best_params_to_metaai,
    )

    # 🏁 Step 3: 王国システムへ最適戦略反映
    apply_to_kingdom = PythonOperator(
        task_id="apply_best_params_to_kingdom",
        python_callable=apply_best_params_to_kingdom,
    )

    # DAGフロー定義: 最適化 → MetaAI再学習 → Kingdom適用
    optimize_worker_1 >> apply_to_metaai >> apply_to_kingdom
