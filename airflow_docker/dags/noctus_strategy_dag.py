#!/usr/bin/env python3
# coding: utf-8

"""
🛡️ Noctus Sentinella Risk Assessment DAG (v2.1 conf対応)
- 守護者ノクトゥスによる市場リスク評価の自動化DAG
- GUI/RESTからのトリガー理由（conf["reason"]）も全タスクで記録・活用可
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from core.path_config import STRATEGIES_DIR

import pandas as pd
import numpy as np

default_args = {
    'owner': 'Noctria',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    dag_id='noctus_strategy_dag',
    default_args=default_args,
    description='🛡️ Noctria Kingdomの守護者Noctusによるリスク評価DAG',
    schedule=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'risk_management', 'noctus'],
)

def veritas_trigger_task(**kwargs):
    ti = kwargs['ti']
    conf = kwargs.get("dag_run").conf if kwargs.get("dag_run") else {}
    reason = conf.get("reason", "理由未指定")
    print(f"【Noctusトリガータスク・発令理由】{reason}")

    dummy_hist_data = pd.DataFrame({
        'Close': np.random.normal(loc=150, scale=2, size=100)
    })
    dummy_hist_data['returns'] = dummy_hist_data['Close'].pct_change().dropna()

    mock_market_data = {
        "price": 152.5,
        "volume": 150,
        "spread": 0.012,
        "volatility": 0.15,
        "historical_data": dummy_hist_data.to_json(),
        "trigger_reason": reason,
    }
    ti.xcom_push(key='market_data', value=mock_market_data)
    ti.xcom_push(key='proposed_action', value="BUY")  # 他臣下の提案（例：BUY）

def noctus_strategy_task(**kwargs):
    ti = kwargs['ti']
    conf = kwargs.get("dag_run").conf if kwargs.get("dag_run") else {}
    reason = conf.get("reason", "理由未指定")
    print(f"【Noctusリスク評価タスク・発令理由】{reason}")

    input_data = ti.xcom_pull(task_ids='veritas_trigger_task', key='market_data')
    proposed_action = ti.xcom_pull(task_ids='veritas_trigger_task', key='proposed_action')

    if input_data is None or proposed_action is None:
        print("⚠️ 必要なデータが存在しません。デフォルト値で進行します。")
        dummy_hist_data = pd.DataFrame({
            'Close': np.random.normal(loc=150, scale=2, size=100)
        })
        input_data = {
            "price": 150.0,
            "volume": 100,
            "spread": 0.01,
            "volatility": 0.10,
            "historical_data": dummy_hist_data.to_json(),
            "trigger_reason": reason,
        }
        proposed_action = "HOLD"

    try:
        from strategies.noctus_sentinella import NoctusSentinella
        input_data['historical_data'] = pd.read_json(input_data['historical_data'])
        noctus = NoctusSentinella()
        decision = noctus.assess(input_data, proposed_action)
        result = {"assessment": decision, "reason": reason}
        ti.xcom_push(key='noctus_assessment', value=result)
        print(f"🛡️ Noctus: 『王よ、この状況のリスク評価は{decision}です。』【発令理由】{reason}")
    except Exception as e:
        print(f"❌ Noctus戦略中にエラー発生: {e}")
        raise

with dag:
    veritas_task = PythonOperator(
        task_id='veritas_trigger_task',
        python_callable=veritas_trigger_task,
        provide_context=True
    )

    noctus_task = PythonOperator(
        task_id='noctus_risk_assessment_task',
        python_callable=noctus_strategy_task,
        provide_context=True
    )

    veritas_task >> noctus_task
