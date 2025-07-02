import sys
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

# ✅ パス集中管理（Noctria Kingdom v2.0設計原則）
from core.path_config import STRATEGIES_DIR

# ✅ PythonPath に戦略ディレクトリを追加（Airflow Worker対応）

# ✅ Noctus戦略クラスの読み込み
from noctus_sentinella import NoctusSentinella

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
    dag_id='noctus_strategy_dag',
    default_args=default_args,
    description='🛡️ Noctria Kingdomの守護者Noctusによるリスク管理戦略DAG',
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'risk_management'],
)

# === Veritas（外部知性）からの市場データ注入 ===
def veritas_trigger_task(ti, **kwargs):
    mock_market_data = {
        "price": 1.2530,
        "price_history": [1.2500, 1.2525, 1.2550, 1.2510, 1.2540],
        "spread": 0.015,
        "volume": 120,
        "order_block": 0.5,
        "volatility": 0.22
    }
    ti.xcom_push(key='market_data', value=mock_market_data)

# === Noctusによるリスク評価タスク ===
def noctus_strategy_task(ti, **kwargs):
    input_data = ti.xcom_pull(task_ids='veritas_trigger_task', key='market_data')

    if input_data is None:
        print("⚠️ Veritasからのデータが無かったため、デフォルトで実行します")
        input_data = {
            "price": 1.0,
            "price_history": [1.0] * 5,
            "spread": 0.01,
            "volume": 100,
            "order_block": 0.0,
            "volatility": 0.1
        }

    noctus = NoctusSentinella()
    decision = noctus.process(input_data)

    ti.xcom_push(key='noctus_decision', value=decision)
    print(f"🛡️ Noctusの判断: {decision}")

# === DAGにタスク登録（指揮官としてのAirflow）
with dag:
    veritas_task = PythonOperator(
        task_id='veritas_trigger_task',
        python_callable=veritas_trigger_task,
    )

    noctus_task = PythonOperator(
        task_id='noctus_risk_management_task',
        python_callable=noctus_strategy_task,
    )

    veritas_task >> noctus_task
