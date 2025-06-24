import sys
sys.path.append('/opt/airflow')

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import random

# 🔽 各戦略クラスをインポート
from strategies.prometheus_oracle import PrometheusOracle
from strategies.aurus_singularis import AurusSingularis
from strategies.levia_tempest import LeviaTempest
from strategies.noctus_sentinella import NoctusSentinella

# === DAG設定 ===
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
    description='🧠 Veritasが市場データを生成し、各AI戦略へ連携する統合DAG',
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'veritas', 'hub'],
)

# === Veritasによる市場データ生成 ===
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
    print(f"🧠 Veritas: 市場データ生成完了 → {market_data}")

# === 各AI戦略の統一実行関数 ===
def run_prometheus(**kwargs):
    market_data = kwargs['ti'].xcom_pull(task_ids='veritas_generate_market_data_task', key='market_data')
    result = PrometheusOracle().process(market_data)
    print(f"🔮 Prometheusの決断: {result}")

def run_aurus(**kwargs):
    market_data = kwargs['ti'].xcom_pull(task_ids='veritas_generate_market_data_task', key='market_data')
    result = AurusSingularis().process(market_data)
    print(f"⚔️ Aurusの決断: {result}")

def run_levia(**kwargs):
    market_data = kwargs['ti'].xcom_pull(task_ids='veritas_generate_market_data_task', key='market_data')
    result = LeviaTempest().process(market_data)
    print(f"⚡ Leviaの決断: {result}")

def run_noctus(**kwargs):
    market_data = kwargs['ti'].xcom_pull(task_ids='veritas_generate_market_data_task', key='market_data')
    result = NoctusSentinella().process(market_data)
    print(f"🛡️ Noctusの決断: {result}")

# === DAGの構築 ===
with dag:
    generate_data_task = PythonOperator(
        task_id='veritas_generate_market_data_task',
        python_callable=generate_market_data,
        provide_context=True,
    )

    prometheus_task = PythonOperator(
        task_id='run_prometheus_strategy',
        python_callable=run_prometheus,
        provide_context=True,
    )

    aurus_task = PythonOperator(
        task_id='run_aurus_strategy',
        python_callable=run_aurus,
        provide_context=True,
    )

    levia_task = PythonOperator(
        task_id='run_levia_strategy',
        python_callable=run_levia,
        provide_context=True,
    )

    noctus_task = PythonOperator(
        task_id='run_noctus_strategy',
        python_callable=run_noctus,
        provide_context=True,
    )

    # 🔁 依存関係の定義：Veritas → 各戦略へ分岐
    generate_data_task >> [prometheus_task, aurus_task, levia_task, noctus_task]
