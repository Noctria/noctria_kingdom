import sys
sys.path.append('/opt/airflow')  # Airflowコンテナルートに対応

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

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
    description='⚔️ Noctria Kingdomの戦術官Aurusによるトレンド解析DAG',
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'trend-analysis'],
)

def veritas_trigger_task(**kwargs):
    ti = kwargs['ti']
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
    ti.xcom_push(key='market_data', value=mock_market_data)

def aurus_strategy_task(**kwargs):
    ti = kwargs['ti']
    input_data = ti.xcom_pull(task_ids='veritas_trigger_task', key='market_data')
    if input_data is None:
        print("⚠️ Veritasからのデータが無かったため、デフォルトで実行します")
        input_data = {k: 0.0 for k in [
            "price", "volume", "sentiment", "trend_strength", "volatility",
            "order_block", "institutional_flow", "short_interest",
            "momentum", "trend_prediction", "liquidity_ratio"
        ]}
        input_data["price"] = 1.0

    try:
        # ✅ 重い import をここに移動
        from strategies.aurus_singularis import AurusSingularis
        aurus = AurusSingularis()
        decision = aurus.process(input_data)
        ti.xcom_push(key='aurus_decision', value=decision)
        print(f"🔮 Aurusの戦略判断: {decision}")
    except Exception as e:
        print(f"❌ Aurus戦略中にエラー発生: {e}")
        raise

with dag:
    veritas_task = PythonOperator(
        task_id='veritas_trigger_task',
        python_callable=veritas_trigger_task,
    )

    aurus_task = PythonOperator(
        task_id='aurus_trend_analysis_task',
        python_callable=aurus_strategy_task,
    )

    veritas_task >> aurus_task
