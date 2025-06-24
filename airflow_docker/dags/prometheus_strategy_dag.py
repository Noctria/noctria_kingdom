import sys
sys.path.append('/opt/airflow')

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from strategies.prometheus_oracle import PrometheusOracle

default_args = {
    'owner': 'Noctria',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    dag_id='prometheus_strategy_dag',
    default_args=default_args,
    description='Noctria Kingdomの臣下Prometheusによる未来予測戦略DAG',
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'forecasting'],
)

# ✨ DAGタスク定義（XCom・Logger対応）
def prometheus_strategy_task(**kwargs):
    from airflow.models import Variable
    print("👑 王Noctria: Prometheus、未来予測を託す！")

    prometheus = PrometheusOracle()

    # mockデータ or futureではkwargsから注入
    market_data = kwargs.get('market_data') or {
        "price": 1.2345,
        "volume": 1000,
        "sentiment": 0.8,
        "trend_strength": 0.7,
        "volatility": 0.15,
        "order_block": 0.6,
        "institutional_flow": 0.8,
        "short_interest": 0.5,
        "momentum": 0.9,
        "trend_prediction": 0.6,
        "liquidity_ratio": 1.2
    }

    forecast = prometheus.predict_market(market_data)
    decision = "HOLD"
    if forecast > 0.6:
        decision = "BUY"
    elif forecast < 0.4:
        decision = "SELL"

    prometheus.logger.info(f"📊 XCom返却: {decision} / score={forecast:.4f}")
    return decision  # ✅ XComで返す

with dag:
    prometheus_task = PythonOperator(
        task_id='prometheus_forecast_task',
        python_callable=prometheus_strategy_task,
        provide_context=True,  # ✅ kwargs有効化
    )
