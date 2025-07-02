import sys
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

# ✅ パス集中管理（v2.0構成）
from core.path_config import STRATEGIES_DIR

# ✅ Airflow Worker用のPYTHONPATH追加（strategies読み込み用）

# ✅ Prometheus予測AIのインポート
from prometheus_oracle import PrometheusOracle

# === DAG共通設定 ===
default_args = {
    'owner': 'Noctria',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# === DAG定義 ===
dag = DAG(
    dag_id='prometheus_strategy_dag',
    default_args=default_args,
    description='🔮 Noctria Kingdomの臣下Prometheusによる未来予測戦略DAG',
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'forecasting'],
)

# === Veritas等からのデータ注入（模擬）
def veritas_trigger_task(ti, **kwargs):
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

# === Prometheus戦略による未来予測
def prometheus_strategy_task(ti, **kwargs):
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

    ti.xcom_push(key='forecast_result', value=forecast)

    # ログ出力
    if forecast > 0.6:
        decision = "BUY"
    elif forecast < 0.4:
        decision = "SELL"
    else:
        decision = "HOLD"

    print(f"🔮 Prometheus: score = {forecast:.4f} → decision = {decision}")

# === DAGにタスク登録 ===
with dag:
    veritas_task = PythonOperator(
        task_id='veritas_trigger_task',
        python_callable=veritas_trigger_task,
    )

    prometheus_task = PythonOperator(
        task_id='prometheus_forecast_task',
        python_callable=prometheus_strategy_task,
    )

    veritas_task >> prometheus_task
