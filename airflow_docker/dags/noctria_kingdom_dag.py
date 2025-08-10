# airflow_docker/dags/noctria_kingdom_dag.py
#!/usr/bin/env python3
# coding: utf-8

"""
👑 Noctria Kingdom Royal Council DAG (Airflow 2.6 互換版)
- 市場観測 → 御前会議 → 王命記録
- GUI/REST の conf（reason 等）を kwargs から受け取る
- get_current_context は使わず、kwargs の context を参照
"""

import os
import json
import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from airflow import DAG
from airflow.operators.python import PythonOperator

# ---- src パスの前提下での正規 import ----
from src.core.path_config import LOGS_DIR

default_args = {
    'owner': 'KingNoctria',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def _serialize_for_json(obj):
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient="records")
    if isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_for_json(x) for x in obj]
    return obj

def _get_reason_from_conf(kwargs) -> str:
    dag_run = kwargs.get("dag_run")
    if dag_run and getattr(dag_run, "conf", None):
        return dag_run.conf.get("reason", "理由未指定")
    return "理由未指定"

with DAG(
    dag_id='noctria_kingdom_royal_council_dag',
    default_args=default_args,
    description='市場を観測し、御前会議を開き、王の最終判断を下すための中心DAG',
    schedule=timedelta(hours=1),
    start_date=datetime(2025, 7, 1),
    catchup=False,
    tags=['noctria', 'kingdom', 'royal_council'],
) as dag:

    def fetch_market_data_task(**kwargs):
        logger = logging.getLogger("MarketObserver")
        logger.setLevel(logging.INFO)
        reason = _get_reason_from_conf(kwargs)
        logger.info(f"【市場観測・発令理由】{reason}")

        # ダミーデータ（本番は fetcher へ置換可）
        dummy_hist = pd.DataFrame({'Close': np.random.normal(loc=150, scale=2, size=100)})
        dummy_hist['returns'] = dummy_hist['Close'].pct_change()

        market_data = {
            "price": float(150.50 + np.random.randn()),
            "previous_price": float(150.48 + np.random.randn()),
            "volume": int(np.random.randint(100, 300)),
            "volatility": float(np.random.uniform(0.1, 0.3)),
            "sma_5_vs_20_diff": float(np.random.uniform(-0.1, 0.1)),
            "macd_signal_diff": float(np.random.uniform(-0.05, 0.05)),
            "trend_strength": float(np.random.uniform(0.3, 0.8)),
            "trend_prediction": str(np.random.choice(["bullish", "bearish", "neutral"])),
            "rsi_14": float(np.random.uniform(30, 70)),
            "stoch_k": float(np.random.uniform(20, 80)),
            "momentum": float(np.random.uniform(0.4, 0.9)),
            "bollinger_upper_dist": float(np.random.uniform(-0.05, 0.05)),
            "bollinger_lower_dist": float(np.random.uniform(-0.05, 0.05)),
            "sentiment": float(np.random.uniform(0.3, 0.9)),
            "order_block": float(np.random.uniform(0.2, 0.8)),
            "liquidity_ratio": float(np.random.uniform(0.8, 1.5)),
            "symbol": "USDJPY",
            "interest_rate_diff": 0.05,
            "cpi_change_rate": 0.03,
            "news_sentiment_score": float(np.random.uniform(0.4, 0.8)),
            "spread": float(np.random.uniform(0.01, 0.02)),
            "historical_data": dummy_hist.to_json(date_format="iso"),
            "trigger_reason": reason,
        }

        kwargs['ti'].xcom_push(key='market_data', value=market_data)
        logger.info("市場の観測完了。データを御前会議に提出します。")
        return market_data

    def hold_council_task(**kwargs):
        # 遅延 import（DAGパースを軽くする）
        from src.core.king_noctria import KingNoctria
        logger = logging.getLogger("RoyalCouncil")
        logger.setLevel(logging.INFO)
        reason = _get_reason_from_conf(kwargs)
        logger.info(f"【御前会議・発令理由】{reason}")

        ti = kwargs['ti']
        market_data = ti.xcom_pull(key='market_data', task_ids='fetch_market_data')
        if not market_data:
            logger.error("市場データが取得できなかったため、会議を中止します。")
            raise ValueError("Market data not found in XComs.")

        # 復元
        hist_json = market_data.get('historical_data')
        if hist_json:
            try:
                market_data['historical_data'] = pd.read_json(hist_json)
            except Exception:
                # 壊れていても続行（会議は可能）
                market_data['historical_data'] = pd.DataFrame()

        king = KingNoctria()
        council_report = king.hold_council(market_data)
        logger.info(f"会議終了。王の最終判断: {council_report.get('final_decision', 'N/A')}")
        ti.xcom_push(key='council_report', value=council_report)
        return council_report

    def log_decision_task(**kwargs):
        logger = logging.getLogger("RoyalScribe")
        logger.setLevel(logging.INFO)
        reason = _get_reason_from_conf(kwargs)
        logger.info(f"【王命記録・発令理由】{reason}")

        ti = kwargs['ti']
        report = ti.xcom_pull(key='council_report', task_ids='hold_council')
        if not report:
            logger.warning("記録すべき報告書が存在しませんでした。")
            return

        report['trigger_reason'] = reason
        serializable = _serialize_for_json(report)

        log_file_path = LOGS_DIR / "kingdom_council_reports" / f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_report.json"
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file_path, 'w', encoding='utf-8') as f:
            json.dump(serializable, f, ensure_ascii=False, indent=4)
        logger.info(f"王命を公式記録として書庫に納めました: {log_file_path}")

    task_fetch_data = PythonOperator(
        task_id='fetch_market_data',
        python_callable=fetch_market_data_task,
        provide_context=True,  # Airflow 2.6系でも安全に kwargs を渡す
    )

    task_hold_council = PythonOperator(
        task_id='hold_council',
        python_callable=hold_council_task,
        provide_context=True,
    )

    task_log_decision = PythonOperator(
        task_id='log_decision',
        python_callable=log_decision_task,
        provide_context=True,
    )

    task_fetch_data >> task_hold_council >> task_log_decision
