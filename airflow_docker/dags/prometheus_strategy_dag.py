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
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'forecasting'],
)

# === Veritasから受け取ったデータをXComに注入するタスク ===
def veritas_trigger_task(**kwargs):
    ti = kwargs['ti']
    # Veritasなど外部から受け取ったと仮定した mock データ
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
    ti.xcom_push(key='market_data', value=mock_market_data)

# === Prometheus戦略による未来予測タスク ===
def prometheus_strategy_task(**kwargs):
    ti = kwargs['ti']
    input_data = ti.xcom_pull(task_ids='veritas_trigger_task', key='market_data')

    if input_data is None:
        print("⚠️ Veritasからのmarket_dataが見つかりません。デフォルト値で実行します")
        input_data = {
            "price": 1.0, "volume": 0.0, "sentiment": 0.5, "trend_strength": 0.5,
            "volatility": 0.1, "order_block": 0.5, "institutional_flow": 0.5,
            "short_interest": 0.5, "momentum": 0.5, "trend_prediction": 0.5,
            "liquidity_ratio": 1.0
        }

    prometheus = PrometheusOracle()
    forecast = prometheus.predict_market(input_data)

    # 予測結果をXComに保存（FastAPI側がpullできる）
    ti.xcom_push(key='forecast_result', value=forecast)

    # ログ出力
    if forecast > 0.6:
        decision = "BUY"
    elif forecast < 0.4:
        decision = "SELL"
    else:
        decision = "HOLD"

    print(f"🔮 Prometheus: score = {forecast:.4f} → decision = {decision}")

# === DAGに登録 ===
with dag:
    veritas_task = PythonOperator(
        task_id='veritas_trigger_task',
        python_callable=veritas_trigger_task,
        provide_context=True
    )

    prometheus_task = PythonOperator(
        task_id='prometheus_forecast_task',
        python_callable=prometheus_strategy_task,
        provide_context=True
    )

    veritas_task >> prometheus_task
