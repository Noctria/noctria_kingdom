from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import timedelta
import sys

# ========================================
# 🏛️ Noctria Kingdom - Veritas EA命令DAG
# ========================================

# ✅ パス集中管理（王国統治ルールに準拠）
from core.path_config import SCRIPTS_DIR, VERITAS_DIR, EXECUTION_DIR

# ✅ Python モジュール参照用に sys.path 追加（Airflow環境下のパス問題対策）
sys.path.append(str(SCRIPTS_DIR))
sys.path.append(str(VERITAS_DIR))
sys.path.append(str(EXECUTION_DIR))

# ✅ 各フェーズ関数を外部からインポート（ロジックはDAGに書かない）
from veritas.evaluate_veritas import evaluate_strategies
from veritas.promote_accepted_strategies import promote_strategies
from execution.generate_order_json import generate_order_json

# ✅ DAG の基本設定
default_args = {
    "owner": "Noctria",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=3),
}

# ✅ DAG定義本体
with DAG(
    dag_id="veritas_to_order_dag",
    description="Veritas戦略 → EA命令JSON生成までの完全自動化DAG",
    default_args=default_args,
    schedule_interval=None,        # 🔁 手動実行前提（定期化は任意）
    start_date=days_ago(1),
    catchup=False,
    tags=["veritas", "pdca", "auto-ea"],
) as dag:

    # 🧪 Check: 戦略評価
    evaluate_task = PythonOperator(
        task_id="evaluate_veritas_strategies",
        python_callable=evaluate_strategies,
    )

    # 🏅 Act: 採用戦略昇格
    promote_task = PythonOperator(
        task_id="promote_accepted_strategies",
        python_callable=promote_strategies,
    )

    # ⚔️ Do: EA命令生成
    generate_order_task = PythonOperator(
        task_id="generate_ea_order_json",
        python_callable=generate_order_json,
    )

    # ✅ フェーズ順に接続
    evaluate_task >> promote_task >> generate_order_task
