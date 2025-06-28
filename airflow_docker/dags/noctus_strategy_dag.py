import sys
sys.path.append('/opt/airflow')  # ✅ Airflowコンテナのルートパスを追加

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from strategies.noctus_sentinella import NoctusSentinella

# === DAG設定 ===
default_args = {
    'owner': 'Noctria',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    dag_id='noctus_strategy_dag',
    default_args=default_args,
    description='🛡️ Noctria Kingdomの守護者Noctusによるリスク管理戦略DAG',
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'risk_management'],
)

# === Veritasなどの外部AIからのmarket_data注入 ===
def veritas_trigger_task(**kwargs):
    ti = kwargs['ti']
    mock_market_data = {
        "price": 1.2530,
        "price_history": [1.2500, 1.2525, 1.2550, 1.2510, 1.2540],
        "spread": 0.015,
        "volume": 120,
        "order_block": 0.5,
        "volatility": 0.22
    }
    ti.xcom_push(key='market_data', value=mock_market_data)

# === Noctusによるリスク判断タスク ===
def noctus_strategy_task(**kwargs):
    ti = kwargs['ti']
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

# === DAGへタスク登録 ===
with dag:
    veritas_task = PythonOperator(
        task_id='veritas_trigger_task',
        python_callable=veritas_trigger_task,
        provide_context=True,
    )

    noctus_task = PythonOperator(
        task_id='noctus_risk_management_task',
        python_callable=noctus_strategy_task,
        provide_context=True,
    )

    veritas_task >> noctus_task
