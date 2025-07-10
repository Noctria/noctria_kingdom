# veritas_master_dag.py

import sys
import os
import json
import random
from datetime import datetime, timedelta

# ✅ パス設定とsys.path追加（Airflow context対応）
from core.path_config import STRATEGIES_DIR, LOGS_DIR
BASE_DIR = str(STRATEGIES_DIR.parent)
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from airflow import DAG
from airflow.operators.python import PythonOperator

# ✅ 四臣インポート
from strategies.prometheus_oracle import PrometheusOracle
from strategies.aurus_singularis import AurusSingularis
from strategies.noctus_sentinella import NoctusSentinella
from strategies.levia_tempest import LeviaTempest

# ✅ GitHub Pushスクリプト
from scripts.push_generated_strategy import push_generated_strategies

# =====================================
# DAG設定
# =====================================
default_args = {
    'owner': 'Noctria',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=2),
}

with DAG(
    dag_id='veritas_master_dag',
    default_args=default_args,
    description='🧠 Veritasが生成した市場データを四臣に渡し、採用戦略をGitHubにPush',
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'veritas', 'hub'],
) as dag:

    # =====================================
    # 1. 市場データ生成タスク（Veritas）
    # =====================================
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

        # ✅ ログとして保存
        os.makedirs(LOGS_DIR, exist_ok=True)
        log_path = LOGS_DIR / "veritas_market_data.json"
        with open(log_path, "w") as f:
            json.dump(market_data, f, indent=2)

    generate_data_task = PythonOperator(
        task_id='veritas_generate_market_data_task',
        python_callable=generate_market_data,
    )

    # =====================================
    # 2. 各AIによる戦略処理
    # =====================================
    def run_prometheus(**kwargs):
        market_data = kwargs['ti'].xcom_pull(task_ids='veritas_generate_market_data_task', key='market_data')
        oracle = PrometheusOracle()
        result = oracle.process(market_data)
        print(f"🔮 Prometheusの戦略判断: {result}")

    def run_aurus(**kwargs):
        market_data = kwargs['ti'].xcom_pull(task_ids='veritas_generate_market_data_task', key='market_data')
        aurus = AurusSingularis()
        result = aurus.process(market_data)
        print(f"⚔️ Aurusの戦略判断: {result}")

    def run_noctus(**kwargs):
        market_data = kwargs['ti'].xcom_pull(task_ids='veritas_generate_market_data_task', key='market_data')
        noctus = NoctusSentinella()
        result = noctus.process(market_data)
        print(f"🛡️ Noctusのリスク判断: {result}")

    def run_levia(**kwargs):
        market_data = kwargs['ti'].xcom_pull(task_ids='veritas_generate_market_data_task', key='market_data')
        levia = LeviaTempest()
        result = levia.process(market_data)
        print(f"⚡ Leviaのスキャル判断: {result}")

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

    # =====================================
    # 3. GitHub Pushタスク（採用戦略）
    # =====================================
    def push_to_github(**kwargs):
        push_generated_strategies()
        print("📤 採用された戦略をGitHubにpushしました")

    push_strategy_task = PythonOperator(
        task_id='push_generated_strategy_to_github',
        python_callable=push_to_github,
    )

    # =====================================
    # DAG依存関係定義
    # =====================================
    generate_data_task >> [prometheus_task, aurus_task, noctus_task, levia_task] >> push_strategy_task
