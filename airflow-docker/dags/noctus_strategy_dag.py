from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from core.levia_tempest import LeviaTempest

default_args = {
    'owner': 'Noctria',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def execute_levia_strategy():
    print("👑 Levia_Tempest: 王国の即応部隊、出撃します！")
    levia_ai = LeviaTempest()
    mock_market_data = {
        "price": 1.2050,
        "previous_price": 1.2040,
        "volume": 150,
        "spread": 0.012,
        "order_block": 0.4,
        "volatility": 0.15
    }
    decision = levia_ai.process(mock_market_data)
    print("👑 Leviaの決断:", decision)

with DAG(
    dag_id='levia_strategy_dag',
    default_args=default_args,
    description='👑 Leviaによるスキャルピング戦略DAG',
    schedule_interval='@hourly',  # 任意で調整
    start_date=datetime(2025, 6, 10),
    catchup=False,
    tags=['noctria_kingdom', 'levia', 'scalping']
) as dag:

    execute_strategy_task = PythonOperator(
        task_id='execute_levia_strategy',
        python_callable=execute_levia_strategy
    )

    execute_strategy_task
