#!/usr/bin/env python3
# coding: utf-8

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from core.path_config import STRATEGIES_DIR

# ===============================
# DAG共通設定
# ===============================
default_args = {
    'owner': 'Noctria',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    dag_id='levia_strategy_dag',
    default_args=default_args,
    description='⚡ Noctria KingdomのLeviaによるスキャルピング戦略DAG',
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'scalping'],
)

# ===============================
# Veritasデータ注入タスク（模擬）
# ===============================
def veritas_trigger_task(ti, **kwargs):
    mock_market_data = {
        "price": 1.2050,
        "previous_price": 1.2040,
        "volume": 150,
        "spread": 0.012,
        "order_block": 0.4,
        "volatility": 0.15
    }
    ti.xcom_push(key='market_data', value=mock_market_data)

# ===============================
# Leviaスキャルピング戦略タスク
# ===============================
def levia_strategy_task(ti, **kwargs):
    input_data = ti.xcom_pull(task_ids='veritas_trigger_task', key='market_data')
    if input_data is None:
        print("⚠️ market_dataが存在しません。デフォルトデータを使用します。")
        input_data = {
            "price": 1.0,
            "previous_price": 1.0,
            "volume": 100,
            "spread": 0.01,
            "order_block": 0.0,
            "volatility": 0.1
        }
    try:
        from strategies.levia_tempest import LeviaTempest  # STRATEGIES_DIR 配下
        levia = LeviaTempest()
        decision = levia.propose(input_data)   # ← `process` ではなく `propose` で統一！（Aurusと揃える）
        ti.xcom_push(key='levia_decision', value=decision)
        print(f"⚡ Levia: 『王よ、我が刃はこの刻、{decision}に振るうと見定めました。』")
    except Exception as e:
        print(f"❌ Levia戦略中にエラー発生: {e}")
        raise

# ===============================
# DAGタスク定義
# ===============================
with dag:
    veritas_task = PythonOperator(
        task_id='veritas_trigger_task',
        python_callable=veritas_trigger_task,
    )

    levia_task = PythonOperator(
        task_id='levia_scalping_task',
        python_callable=levia_strategy_task,
    )

    veritas_task >> levia_task
