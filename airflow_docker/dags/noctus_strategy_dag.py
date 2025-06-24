import sys
sys.path.append('/opt/airflow')

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from strategies.noctus_sentinella import NoctusSentinella

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
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'risk_management'],
)

def noctus_strategy_task(**kwargs):
    print("👑 王Noctria: Noctusよ、王国の資産を守るため、慎重かつ果断に動け。")

    noctus = NoctusSentinella()

    market_data = kwargs.get("market_data") or {
        "price": 1.2530,
        "price_history": [1.2500, 1.2525, 1.2550, 1.2510, 1.2540],
        "spread": 0.015,
        "volume": 120,
        "order_block": 0.5,
        "volatility": 0.22
    }

    decision = noctus.process(market_data)
    noctus.logger.info(f"🛡️ Noctusのリスク判断（XCom返却）: {decision}")
    print(f"🛡️ Noctusの決断: {decision}")
    return decision

with dag:
    noctus_task = PythonOperator(
        task_id='noctus_risk_management_task',
        python_callable=noctus_strategy_task,
        provide_context=True,  # ✅ kwargs有効化
    )
