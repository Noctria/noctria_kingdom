import sys
sys.path.append('/opt/airflow')  # Airflow コンテナ用パス追加入力

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from core.noctria import Noctria

# ✅ DAG共通設定
default_args = {
    'owner': 'Noctria',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# ✅ DAG定義
dag = DAG(
    dag_id='noctria_royal_dag',
    default_args=default_args,
    description='👑 Noctria王の統合戦略判断DAG',
    schedule_interval=None,  # 例: "0 * * * *" で毎時実行など
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'royal', 'decision'],
)

def royal_decision_task():
    print("📜 Noctria王、すべてのAIの声を聞き最終判断を下します。")
    king = Noctria()
    result = king.execute_trade()
    print(f"👑 最終戦略判断: {result}")

# ✅ DAGにタスク追加
with dag:
    royal_task = PythonOperator(
        task_id='noctria_royal_decision_task',
        python_callable=royal_decision_task,
        dag=dag,
    )
