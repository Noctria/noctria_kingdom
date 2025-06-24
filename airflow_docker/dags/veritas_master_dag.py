import sys
sys.path.append('/opt/airflow')

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import random

default_args = {
    'owner': 'Noctria',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=2),
}

dag = DAG(
    dag_id='veritas_master_dag',
    default_args=default_args,
    description='🧠 Veritasから各AI戦略DAGへmarket_dataを連携するハブDAG',
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'veritas', 'hub'],
)

# === Veritasのデータ生成（モック） ===
def generate_market_data(**kwargs):
    ti = kwargs['ti']
    market_data = {
        "price": round(random.uniform(1.2, 1.3), 4),
        "volume": random.randint(100, 1000),
        "sentiment": round(random.uniform(0.0, 1.0), 2),
        "trend_strength": round(random.uniform(0.0, 1.0), 2),
        "volatility": round(random.uniform(0.05, 0.3), 2),
        "order_block": round(random.uniform(0.0, 1.0), 2),
        "institutional_flow": round(random.uniform(0.0, 1.0), 2),
        "short_interest": round(random.uniform(0.0, 1.0), 2),
        "momentum": round(random.uniform(0.0, 1.0), 2),
        "trend_prediction": round(random.uniform(0.0, 1.0), 2),
        "liquidity_ratio": round(random.uniform(0.5, 2.0), 2),
        "spread": round(random.uniform(0.01, 0.05), 3),
        "previous_price": round(random.uniform(1.2, 1.3), 4),
        "price_history": [1.25, 1.255, 1.26, 1.252],
    }
    ti.xcom_push(key='market_data', value=market_data)
    print(f"🧠 Veritasが生成した市場データ: {market_data}")

with dag:
    generate_data_task = PythonOperator(
        task_id='veritas_generate_market_data_task',
        python_callable=generate_market_data,
        provide_context=True,
    )
