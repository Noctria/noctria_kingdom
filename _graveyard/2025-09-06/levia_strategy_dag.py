#!/usr/bin/env python3
# coding: utf-8

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from core.path_config import STRATEGIES_DIR

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

def veritas_trigger_task(**kwargs):
    ti = kwargs['ti']
    conf = kwargs.get("dag_run").conf if kwargs.get("dag_run") else {}
    reason = conf.get("reason", "理由未指定")
    print(f"【Leviaトリガータスク・発令理由】{reason}")
    mock_market_data = {
        "price": 1.2050,
        "previous_price": 1.2040,
        "volume": 150,
        "spread": 0.012,
        "order_block": 0.4,
        "volatility": 0.15,
        "trigger_reason": reason,  # 理由もデータに付加
    }
    ti.xcom_push(key='market_data', value=mock_market_data)

def levia_strategy_task(**kwargs):
    ti = kwargs['ti']
    conf = kwargs.get("dag_run").conf if kwargs.get("dag_run") else {}
    reason = conf.get("reason", "理由未指定")
    print(f"【Leviaスキャルピングタスク・発令理由】{reason}")
    input_data = ti.xcom_pull(task_ids='veritas_trigger_task', key='market_data')
    if input_data is None:
        print("⚠️ market_dataが存在しません。デフォルトデータを使用します。")
        input_data = {
            "price": 1.0,
            "previous_price": 1.0,
            "volume": 100,
            "spread": 0.01,
            "order_block": 0.0,
            "volatility": 0.1,
            "trigger_reason": reason,
        }
    try:
        from strategies.levia_tempest import LeviaTempest  # STRATEGIES_DIR 配下
        levia = LeviaTempest()
        decision = levia.propose(input_data)
        result = {"decision": decision, "reason": reason}
        ti.xcom_push(key='levia_decision', value=result)
        print(f"⚡ Levia: 『王よ、我が刃はこの刻、{decision}に振るうと見定めました。』【発令理由】{reason}")
    except Exception as e:
        print(f"❌ Levia戦略中にエラー発生: {e}")
        raise

with dag:
    veritas_task = PythonOperator(
        task_id='veritas_trigger_task',
        python_callable=veritas_trigger_task,
        provide_context=True
    )

    levia_task = PythonOperator(
        task_id='levia_scalping_task',
        python_callable=levia_strategy_task,
        provide_context=True
    )

    veritas_task >> levia_task
