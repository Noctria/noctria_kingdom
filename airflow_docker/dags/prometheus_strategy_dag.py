#!/usr/bin/env python3
# coding: utf-8

"""
🔮 Prometheus Oracle Forecast DAG (v2.1 conf対応)
- 未来予測官プロメテウスによる定期的な未来予測DAG
- GUI/RESTトリガー時、conf["reason"]（発令理由）も全タスクで記録・活用可
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from core.path_config import ORACLE_FORECAST_JSON

import logging

default_args = {
    'owner': 'Prometheus',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    dag_id='prometheus_strategy_dag',
    default_args=default_args,
    description='🔮 Noctria Kingdomの未来予測官Prometheusによる予測DAG',
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'forecasting', 'prometheus'],
)

def veritas_trigger_task(**kwargs):
    # もし将来XComや外部連携で使いたい場合に拡張
    conf = kwargs.get("dag_run").conf if kwargs.get("dag_run") else {}
    reason = conf.get("reason", "理由未指定")
    print(f"【Prometheusトリガータスク・発令理由】{reason}")
    # 必要ならXComに理由を記録しても良い

def prometheus_forecast_task(**kwargs):
    conf = kwargs.get("dag_run").conf if kwargs.get("dag_run") else {}
    reason = conf.get("reason", "理由未指定")
    try:
        from strategies.prometheus_oracle import PrometheusOracle
        import pandas as pd

        logger = logging.getLogger("PrometheusForecast")
        logger.info(f"【未来予測発令理由】{reason}")
        logger.info("神託の儀を開始します…")

        oracle = PrometheusOracle()
        predictions_df = oracle.predict_with_confidence(n_days=30)
        if predictions_df is None or (hasattr(predictions_df, "empty") and predictions_df.empty):
            logger.warning("神託が得られませんでした。")
            return

        ORACLE_FORECAST_JSON.parent.mkdir(parents=True, exist_ok=True)
        predictions_df.to_json(ORACLE_FORECAST_JSON, orient="records", force_ascii=False, indent=4)
        logger.info(f"神託を保存: {ORACLE_FORECAST_JSON}")

        # 理由もXComへ（分析履歴トレース用）
        ti = kwargs['ti']
        ti.xcom_push(key='prometheus_forecast', value={
            "head": predictions_df.head(1).to_dict("records"),
            "trigger_reason": reason
        })
    except Exception as e:
        logger = logging.getLogger("PrometheusForecast")
        logger.error(f"神託タスク中にエラー: {e}", exc_info=True)
        raise

with dag:
    # veritas_task = PythonOperator(
    #     task_id='veritas_trigger_task',
    #     python_callable=veritas_trigger_task,
    #     provide_context=True
    # )

    forecast_task = PythonOperator(
        task_id='prometheus_oracle_forecast_task',
        python_callable=prometheus_forecast_task,
        provide_context=True
    )

    # 必要ならveritas_task >> forecast_task
    forecast_task
