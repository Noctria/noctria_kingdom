import sys
import os
import json
import random
from datetime import datetime, timedelta

sys.path.append('/opt/airflow')  # Airflowコンテナ内の参照パス

from airflow import DAG
from airflow.operators.python import PythonOperator
from strategies.prometheus_oracle import PrometheusOracle
from strategies.aurus_singularis import AurusSingularis
from strategies.noctus_sentinella import NoctusSentinella
from strategies.levia_tempest import LeviaTempest

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
    description='🧠 Veritasから各AI戦略DAGへmarket_dataを連携・評価・採用する統合DAG',
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'veritas', 'hub'],
)

# === Veritas: 市場データ生成 ===
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

    # JSONログ保存（GUI連携用）
    log_dir = "/noctria_kingdom/airflow_docker/logs"
    os.makedirs(log_dir, exist_ok=True)
    with open(os.path.join(log_dir, "veritas_market_data.json"), "w") as f:
        json.dump(market_data, f, indent=2)

# === 各AIモジュールの実行 ===
def run_prometheus(**kwargs):
    ti = kwargs['ti']
    market_data = ti.xcom_pull(task_ids='veritas_generate_market_data_task', key='market_data')
    result = PrometheusOracle().process(market_data)
    ti.xcom_push(key='result', value=result)
    print(f"🔮 Prometheusの戦略判断: {result}")

def run_aurus(**kwargs):
    ti = kwargs['ti']
    market_data = ti.xcom_pull(task_ids='veritas_generate_market_data_task', key='market_data')
    result = AurusSingularis().process(market_data)
    ti.xcom_push(key='result', value=result)
    print(f"⚔️ Aurusの戦略判断: {result}")

def run_noctus(**kwargs):
    ti = kwargs['ti']
    market_data = ti.xcom_pull(task_ids='veritas_generate_market_data_task', key='market_data')
    result = NoctusSentinella().process(market_data)
    ti.xcom_push(key='result', value=result)
    print(f"🛡️ Noctusのリスク判断: {result}")

def run_levia(**kwargs):
    ti = kwargs['ti']
    market_data = ti.xcom_pull(task_ids='veritas_generate_market_data_task', key='market_data')
    result = LeviaTempest().process(market_data)
    ti.xcom_push(key='result', value=result)
    print(f"⚡ Leviaのスキャル判断: {result}")

# === 評価 & 採用 ===
def evaluate_strategies(**kwargs):
    ti = kwargs['ti']
    results = {
        'prometheus': ti.xcom_pull(task_ids='run_prometheus', key='result'),
        'aurus': ti.xcom_pull(task_ids='run_aurus', key='result'),
        'noctus': ti.xcom_pull(task_ids='run_noctus', key='result'),
        'levia': ti.xcom_pull(task_ids='run_levia', key='result'),
    }
    scores = {k: random.uniform(0, 1) for k in results}  # ← 将来的には本物の評価指標に
    best = max(scores, key=scores.get)
    ti.xcom_push(key='selected_ai', value=best)
    print(f"📊 評価スコア: {scores} ➜ 採用: {best}")

def adopt_strategy(**kwargs):
    ti = kwargs['ti']
    selected = ti.xcom_pull(task_ids='evaluate_strategies_task', key='selected_ai')
    print(f"✅ 採用戦略AI: {selected}")
    # TODO: 実際に .py 戦略ファイル保存や Git push 処理を追加可能

# === DAG定義 ===
with dag:
    generate_data_task = PythonOperator(
        task_id='veritas_generate_market_data_task',
        python_callable=generate_market_data,
        provide_context=True,
    )

    prometheus_task = PythonOperator(
        task_id='run_prometheus',
        python_callable=run_prometheus,
        provide_context=True,
    )
    aurus_task = PythonOperator(
        task_id='run_aurus',
        python_callable=run_aurus,
        provide_context=True,
    )
    noctus_task = PythonOperator(
        task_id='run_noctus',
        python_callable=run_noctus,
        provide_context=True,
    )
    levia_task = PythonOperator(
        task_id='run_levia',
        python_callable=run_levia,
        provide_context=True,
    )

    evaluate_strategies_task = PythonOperator(
        task_id='evaluate_strategies_task',
        python_callable=evaluate_strategies,
        provide_context=True,
    )

    adopt_strategy_task = PythonOperator(
        task_id='adopt_strategy_task',
        python_callable=adopt_strategy,
        provide_context=True,
    )

    # 依存関係
    generate_data_task >> [prometheus_task, aurus_task, noctus_task, levia_task]
    [prometheus_task, aurus_task, noctus_task, levia_task] >> evaluate_strategies_task >> adopt_strategy_task
