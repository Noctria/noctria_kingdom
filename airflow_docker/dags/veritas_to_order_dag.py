from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import timedelta
import sys
from core.path_config import SCRIPTS_DIR, VERITAS_DIR, EXECUTION_DIR

# ✅ Python モジュール参照用に sys.path 追加
sys.path.append(str(SCRIPTS_DIR))
sys.path.append(str(VERITAS_DIR))
sys.path.append(str(EXECUTION_DIR))

# ✅ 実行関数のインポート（外部スクリプトに責務を委譲）
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

with DAG(
    dag_id="veritas_to_order_dag",
    description="Veritas戦略 → EA命令生成までを自動化",
    default_args=default_args,
    schedule_interval=None,
    start_date=days_ago(1),
    catchup=False,
    tags=["veritas", "pdca", "auto-ea"],
) as dag:

    # 🧪 Check: 戦略評価
    evaluate = PythonOperator(
        task_id="evaluate_veritas_strategies",
        python_callable=evaluate_strategies,
    )

    # 🏅 Act: 採用戦略昇格
    promote = PythonOperator(
        task_id="promote_accepted_strategies",
        python_callable=promote_strategies,
    )

    # ⚔️ Do: EA命令生成
    generate_order = PythonOperator(
        task_id="generate_ea_order_json",
        python_callable=generate_order_json,
    )

    # ✅ 実行順序
    evaluate >> promote >> generate_order
