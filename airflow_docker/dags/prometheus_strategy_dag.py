import sys
sys.path.append('/opt/airflow')  # ✅ AirflowコンテナのPYTHONPATHを明示

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from strategies.prometheus_oracle import PrometheusOracle

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
    dag_id='prometheus_strategy_dag',
    default_args=default_args,
    description='Noctria Kingdomの臣下Prometheusによる未来予測戦略DAG',
    schedule_interval=None,  # 必要に応じてスケジュール設定
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'forecasting'],
)

# === Prometheus戦略タスク定義 ===
def prometheus_strategy_task():
    print("👑 王Noctria: Prometheus、未来予測を託す！")
    
    prometheus = PrometheusOracle()
    mock_market_data = {
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
    
    forecast = prometheus.predict_market(mock_market_data)
    print(f"🔮 Prometheusの予測: {forecast:.4f}")
    
    if forecast > 0.6:
        decision = "BUY"
    elif forecast < 0.4:
        decision = "SELL"
    else:
        decision = "HOLD"
    
    print(f"⚔️ Prometheusの戦略判断: {decision}")

# === DAGへ登録 ===
with dag:
    prometheus_task = PythonOperator(
        task_id='prometheus_forecast_task',
        python_callable=prometheus_strategy_task,
        dag=dag,
    )
