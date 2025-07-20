#!/usr/bin/env python3
# coding: utf-8

"""
🔮 Prometheus Oracle Forecast DAG (v2.0)
- 未来予測官プロメテウスによる定期的な未来予測DAG（テンプレ化・統一スタイル）
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from core.path_config import ORACLE_FORECAST_JSON

import logging

# ===============================
# DAG共通設定
# ===============================
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
    schedule_interval=None,   # 任意実行。定期化する場合は"@daily"など
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'forecasting', 'prometheus'],
)

# ===============================
# Veritasデータ注入タスク（不要なら省略可）
# ===============================
def veritas_trigger_task(ti, **kwargs):
    # 必要に応じて外部入力やXComで他AIと連携したい場合のみ
    pass

# ===============================
# Prometheus予測タスク
# ===============================
def prometheus_forecast_task(ti, **kwargs):
    try:
        from strategies.prometheus_oracle import PrometheusOracle
        import pandas as pd

        logger = logging.getLogger("PrometheusForecast")
        logger.info("神託の儀を開始します…")

        oracle = PrometheusOracle()
        predictions_df = oracle.predict_with_confidence(n_days=30)
        if predictions_df is None or (hasattr(predictions_df, "empty") and predictions_df.empty):
            logger.warning("神託が得られませんでした。")
            return

        ORACLE_FORECAST_JSON.parent.mkdir(parents=True, exist_ok=True)
        predictions_df.to_json(ORACLE_FORECAST_JSON, orient="records", force_ascii=False, indent=4)
        logger.info(f"神託を保存: {ORACLE_FORECAST_JSON}")

        ti.xcom_push(key='prometheus_forecast', value=predictions_df.head(1).to_dict("records"))  # サンプルXCom
    except Exception as e:
        logger.error(f"神託タスク中にエラー: {e}", exc_info=True)
        raise

# ===============================
# DAGタスク定義
# ===============================
with dag:
    forecast_task = PythonOperator(
        task_id='prometheus_oracle_forecast_task',
        python_callable=prometheus_forecast_task,
    )

    # 必要ならveritas_task >> forecast_task
    forecast_task
