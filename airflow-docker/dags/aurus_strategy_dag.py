import sys
sys.path.append('/opt/airflow')  # ✅ AirflowコンテナのPYTHONPATHを明示

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from core.aurus_singularis import AurusSingularis

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
    dag_id='aurus_strategy_dag',
    default_args=default_args,
    description='Noctria Kingdomの臣下Aurusによるトレンド解析DAG',
    schedule_interval=None,  # 必要に応じてスケジュール設定
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'trend-analysis'],
)

def aurus_strategy_task():
    print("👑 王Noctria: Aurusよ、歴史の潮流を読み解き、我が王国を導け！")
    aurus = AurusSingularis()
    mock_market_data = {
        "price": 1.2345,
        "volume": 500,
        "sentiment": 0.7,
        "trend_strength": 0.5,
        "volatility": 0.12,
        "order_block": 0.3,
        "institutional_flow": 0.6,
        "short_interest": 0.4,
        "momentum": 0.8,
        "trend_prediction": 0.65,
        "liquidity_ratio": 1.1
    }
    decision = aurus.process(mock_market_data)
    print(f"🔮 Aurusの市場トレンド解析結果: {decision}")

with dag:
    aurus_task = PythonOperator(
        task_id='aurus_trend_analysis_task',
        python_callable=aurus_strategy_task,
        dag=dag,
    )
