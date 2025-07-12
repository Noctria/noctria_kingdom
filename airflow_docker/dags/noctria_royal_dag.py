# coding: utf-8

import sys
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

# ✅ パス管理（遅延import不要、軽量な定数）
from core.path_config import CORE_DIR, DAGS_DIR, DATA_DIR, INSTITUTIONS_DIR, LOGS_DIR, MODELS_DIR, PLUGINS_DIR, SCRIPTS_DIR, STRATEGIES_DIR, TESTS_DIR, TOOLS_DIR, VERITAS_DIR

# === DAG共通設定 ===
default_args = {
    'owner': 'Noctria',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# === DAG定義 ===
dag = DAG(
    dag_id='noctria_royal_dag',
    default_args=default_args,
    description='👑 Noctria王の最終戦略判断DAG（統合AIによる決定）',
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'royal', 'decision'],
)

# === 王の意思決定ロジック（遅延importで対応） ===
def royal_decision_task():
    print("📜 王Noctria: 四臣の報を受け取り、今こそ我が決断を示す時……！")

    # ✅ 重い依存モジュールを遅延インポート
    from noctria_ai.noctria import Noctria  # ← transformers, torch 等を含む場合もある

    king = Noctria()
    result = king.execute_trade()
    print(f"👑 王の御宣託：{result}")

# === DAGにタスクを登録 ===
with dag:
    royal_task = PythonOperator(
        task_id='noctria_royal_decision_task',
        python_callable=royal_decision_task,
    )
