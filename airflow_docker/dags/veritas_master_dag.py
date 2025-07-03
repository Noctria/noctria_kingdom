from core.path_config import CORE_DIR, DAGS_DIR, DATA_DIR, INSTITUTIONS_DIR, LOGS_DIR, MODELS_DIR, PLUGINS_DIR, SCRIPTS_DIR, STRATEGIES_DIR, TESTS_DIR, TOOLS_DIR, VERITAS_DIR
import os
import json
import random
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

# ✅ Noctria Kingdom パス集中管理
from core.path_config import LOGS_DIR

# ✅ 各AI戦略
from strategies.prometheus_oracle import PrometheusOracle
from strategies.aurus_singularis import AurusSingularis
from strategies.noctus_sentinella import NoctusSentinella
from strategies.levia_tempest import LeviaTempest

# ✅ GitHub Push用スクリプト
from scripts.push_generated_strategy import push_generated_strategies

# === DAG共通設定 ===
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
    description='🧠 Veritasが生成したmarket_dataを四臣に伝え、戦略をGitHubへpush',
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'veritas', 'hub'],
)

# === Veritasによる市場データ生成タスク ===
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
    print(f"🧠 Veritasが生成した市場データ: {market_data}")

    # ✅ ログファイルに保存（GUI用）
    os.makedirs(LOGS_DIR, exist_ok=True)
    log_path = LOGS_DIR / "veritas_market_data.json"
    with open(log_path, "w") as f:
        json.dump(market_data, f, indent=2)

# === 各AIによる処理タスク ===
def run_prometheus(**kwargs):
    market_data = kwargs['ti'].xcom_pull(task_ids='veritas_generate_market_data_task', key='market_data')
    result = PrometheusOracle().process(market_data)
    print(f"🔮 Prometheusの戦略判断: {result}")

def run_aurus(**kwargs):
    market_data = kwargs['ti'].xcom_pull(task_ids='veritas_generate_market_data_task', key='market_data')
    result = AurusSingularis().process(market_data)
    print(f"⚔️ Aurusの戦略判断: {result}")

def run_noctus(**kwargs):
    market_data = kwargs['ti'].xcom_pull(task_ids='veritas_generate_market_data_task', key='market_data')
    result = NoctusSentinella().process(market_data)
    print(f"🛡️ Noctusのリスク判断: {result}")

def run_levia(**kwargs):
    market_data = kwargs['ti'].xcom_pull(task_ids='veritas_generate_market_data_task', key='market_data')
    result = LeviaTempest().process(market_data)
    print(f"⚡ Leviaのスキャル判断: {result}")

# === 採用戦略 GitHub Push タスク ===
def push_to_github(**kwargs):
    push_generated_strategies()
    print("📤 採用された戦略をGitHubにpushしました")

# === DAG登録 ===
with dag:
    generate_data_task = PythonOperator(
        task_id='veritas_generate_market_data_task',
        python_callable=generate_market_data,
    )

    prometheus_task = PythonOperator(
        task_id='run_prometheus',
        python_callable=run_prometheus,
    )

    aurus_task = PythonOperator(
        task_id='run_aurus',
        python_callable=run_aurus,
    )

    noctus_task = PythonOperator(
        task_id='run_noctus',
        python_callable=run_noctus,
    )

    levia_task = PythonOperator(
        task_id='run_levia',
        python_callable=run_levia,
    )

    push_strategy_task = PythonOperator(
        task_id='push_generated_strategy_to_github',
        python_callable=push_to_github,
    )

    # DAG依存関係構築
    generate_data_task >> [prometheus_task, aurus_task, noctus_task, levia_task] >> push_strategy_task