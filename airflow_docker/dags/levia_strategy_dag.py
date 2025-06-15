import sys
sys.path.append('/opt/airflow')  # ✅ AirflowコンテナのPYTHONPATHを明示

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from strategies.levia_tempest import LeviaTempest

# === DAG共通設定 ===
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
    description='⚔️ Noctria Kingdomの戦術官Leviaによるスキャルピング戦略DAG',
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'scalping'],
)

# === Leviaの任務関数 ===
def levia_strategy_task():
    print("👑 王Noctria: 『Leviaよ、風よりも早く、機を断て！』")
    
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
    print(f"⚔️ Levia: 『王よ、我が刃はこの刻、{decision}に振るうと見定めました。』")

# === DAGにタスク登録 ===
with dag:
    levia_task = PythonOperator(
        task_id='levia_scalping_task',
        python_callable=levia_strategy_task,
    )
