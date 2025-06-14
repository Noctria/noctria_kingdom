import sys
sys.path.append('/opt/airflow')  # ✅ Airflowコンテナのルートパスを追加

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from strategies.noctus_sentinella import NoctusSentinella

# ✅ DAG設定
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
    description='Noctria Kingdomの臣下Noctusによるリスク管理戦略DAG',
    schedule_interval=None,  # 必要に応じてスケジュール設定（例: "@daily"など）
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'risk_management'],
)

def noctus_strategy_task():
    print("👑 王Noctria: Noctus、リスク管理を任せるぞ。")
    noctus = NoctusSentinella()
    mock_market_data = {
        "price": 1.2530,
        "price_history": [1.2500, 1.2525, 1.2550, 1.2510, 1.2540],
        "spread": 0.015,
        "volume": 120,
        "order_block": 0.5,
        "volatility": 0.22
    }
    decision = noctus.process(mock_market_data)
    print(f"🛡️ Noctusの決断: {decision}")

with dag:
    noctus_task = PythonOperator(
        task_id='noctus_risk_management_task',
        python_callable=noctus_strategy_task,
        dag=dag,
    )
