from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import sys

# ========================================
# 🔁 DAG構成：Actフェーズ記録ログを保存
# ========================================

# ✅ パス管理モジュールの追加（Noctria Kingdom標準構成）
from core.path_config import VERITAS_DIR
import os
sys.path.append(str(VERITAS_DIR))

# ✅ 実行対象スクリプト
SCRIPT_PATH = VERITAS_DIR / "record_act_log.py"

default_args = {
    "owner": "Noctria",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    dag_id="veritas_act_record_dag",
    default_args=default_args,
    description="Veritas: 採用戦略をActログに記録",
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["veritas", "act", "pdca"],
) as dag:

    def run_record_act_log():
        print(f"⚙️ 実行中: {SCRIPT_PATH}")
        os.system(f"python {SCRIPT_PATH}")

    record_act = PythonOperator(
        task_id="record_act_log",
        python_callable=run_record_act_log,
    )

    record_act
