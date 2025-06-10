import sys
sys.path.append('/opt/airflow')  # ✅ AirflowコンテナのPYTHONPATHを明示

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from core.levia_tempest import LeviaTempest

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
    dag_id='levia_strategy_dag',
    default_args=default_args,
    description='Noctria Kingdomの臣下Leviaによるスキャルピング戦略DAG',
    schedule_interval=None,  # 必要に応じてスケジュール設定
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'scalping'],
)

def levia_strategy_task():
    print("👑 王Noctria: Leviaよ、嵐の如く瞬間の機を見極めよ！")
    levia = LeviaTempest()
    mock_market_data = {
        "price": 1.2050,
        "previous_price": 1.2040,
        "volume": 150,
        "spread": 0.012,
        "order_block": 0.4,
        "volatility": 0.15
    }
    decision = levia.process(mock_market_data)
    print(f"⚔️ Leviaのスキャルピング戦略判断: {decision}")

with dag:
    levia_task = PythonOperator(
        task_id='levia_scalping_task',
        python_callable=levia_strategy_task,
        dag=dag,
    )
