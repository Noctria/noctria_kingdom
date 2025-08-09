#!/usr/bin/env python3
# coding: utf-8
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pendulum
from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.utils.session import provide_session
from airflow.utils.context import get_current_context

from src.core.path_config import LOGS_DIR, DATA_DIR
from src.core.data.market_data_fetcher import MarketDataFetcher
from src.core.king_noctria import KingNoctria

JST = pendulum.timezone("Asia/Tokyo")

default_args = dict(
    owner="KingNoctria",
    depends_on_past=False,
    email_on_failure=False,
    email_on_retry=False,
    retries=1,
    retry_delay=timedelta(minutes=5),
)

with DAG(
    dag_id="noctria_kingdom_royal_council_dag",
    default_args=default_args,
    description="市場観測→御前会議→王命記録の統合DAG",
    schedule="0 * * * *",          # ← Airflow 2.7+ では schedule推奨
    start_date=datetime(2025, 7, 1, tzinfo=JST),
    catchup=False,
    tags=["noctria", "kingdom", "royal_council"],
) as dag:

    def fetch_market_data_task(**_):
        ctx = get_current_context()
        conf = ctx.get("dag_run").conf if ctx.get("dag_run") else {}
        reason = conf.get("reason", "理由未指定")
        logger = logging.getLogger("MarketObserver")
        logger.info("【市場観測・発令理由】%s", reason)

        # ① 実装があればこちらを使う
        # df_hist = MarketDataFetcher(symbol="USDJPY", lookback=100).fetch()
        # ダミー：将来Fetcherに置換
        df_hist = pd.DataFrame({"Close": np.random.normal(loc=150, scale=2, size=100)})
        df_hist["returns"] = df_hist["Close"].pct_change()
        df_hist = df_hist.dropna().reset_index(drop=True)

        market_data = dict(
            price=float(150.5 + np.random.randn()),
            previous_price=float(150.48 + np.random.randn()),
            volume=int(np.random.randint(100, 300)),
            volatility=float(np.random.uniform(0.1, 0.3)),
            sma_5_vs_20_diff=float(np.random.uniform(-0.1, 0.1)),
            macd_signal_diff=float(np.random.uniform(-0.05, 0.05)),
            trend_strength=float(np.random.uniform(0.3, 0.8)),
            trend_prediction=str(np.random.choice(["bullish", "bearish", "neutral"])),
            rsi_14=float(np.random.uniform(30, 70)),
            stoch_k=float(np.random.uniform(20, 80)),
            momentum=float(np.random.uniform(0.4, 0.9)),
            bollinger_upper_dist=float(np.random.uniform(-0.05, 0.05)),
            bollinger_lower_dist=float(np.random.uniform(-0.05, 0.05)),
            sentiment=float(np.random.uniform(0.3, 0.9)),
            order_block=float(np.random.uniform(0.2, 0.8)),
            liquidity_ratio=float(np.random.uniform(0.8, 1.5)),
            symbol="USDJPY",
            interest_rate_diff=0.05,
            cpi_change_rate=0.03,
            news_sentiment_score=float(np.random.uniform(0.4, 0.8)),
            spread=float(np.random.uniform(0.01, 0.02)),
        )

        # ② XComに大きなDFを載せない：ファイルに保存しパスだけ渡す
        data_dir = (DATA_DIR / "royal_council").resolve()
        data_dir.mkdir(parents=True, exist_ok=True)
        ts = pendulum.now("UTC").to_datetime_string().replace(":", "-").replace(" ", "_")
        hist_path = data_dir / f"{ts}_historical.parquet"
        df_hist.to_parquet(hist_path)

        # ③ XComには軽量データ＋パス
        xcom_payload = dict(market_data=market_data, historical_path=str(hist_path))
        return xcom_payload

    def hold_council_task(**_):
        ctx = get_current_context()
        logger = logging.getLogger("RoyalCouncil")

        x = ctx["ti"].xcom_pull(task_ids="fetch_market_data")
        if not x:
            raise ValueError("Market data XCom missing.")
        market_data = x["market_data"]
        hist_path = Path(x["historical_path"])
        df_hist = pd.read_parquet(hist_path)

        king = KingNoctria()
        council_report = king.hold_council({**market_data, "historical_data": df_hist})

        # ④ 将来：ここでP層PreTradeValidatorへ送る/VRをC層にログ…のフックを用意
        return council_report

    def log_decision_task(**_):
        ctx = get_current_context()
        logger = logging.getLogger("RoyalScribe")
        conf = ctx.get("dag_run").conf if ctx.get("dag_run") else {}
        reason = conf.get("reason", "理由未指定")

        report = ctx["ti"].xcom_pull(task_ids="hold_council")
        if not report:
            logger.warning("記録対象の報告書なし。")
            return

        # DataFrame等はここでは来ない想定（council_reportはシリアライズ済みを前提）
        report["trigger_reason"] = reason

        out_dir = (LOGS_DIR / "kingdom_council_reports").resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        fp = out_dir / f"{pendulum.now('Asia/Tokyo').format('YYYY-MM-DD_HH-mm-ss')}_report.json"
        with fp.open("w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info("王命を記録: %s", fp)

    start = EmptyOperator(task_id="start")
    task_fetch = PythonOperator(task_id="fetch_market_data", python_callable=fetch_market_data_task)
    task_council = PythonOperator(task_id="hold_council", python_callable=hold_council_task)
    task_log = PythonOperator(task_id="log_decision", python_callable=log_decision_task)
    end = EmptyOperator(task_id="end")

    start >> task_fetch >> task_council >> task_log >> end
