#!/usr/bin/env python3
# coding: utf-8

"""
👑 Noctria Kingdom Royal Council DAG (v2.1)
- 定期的に御前会議を自動開催し、王国の最終的な意思決定を行うための統合DAG。
- 市場データの観測から、王命の下達までを一気通貫で実行する。
"""

import logging
import json
import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator

# ✅ 修正: Airflowが'src'モジュールを見つけられるように、プロジェクトルートをシステムパスに追加
# このDAGファイルが置かれているディレクトリの2階層上がプロジェクトルート（/opt/airflow）になる
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- 王国の基盤モジュールをインポート ---
from src.core.path_config import LOGS_DIR
from src.core.data_loader import MarketDataFetcher
from src.core.king_noctria import KingNoctria

# ========================================
# 👑 DAG共通設定
# ========================================
default_args = {
    'owner': 'KingNoctria',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# ========================================
# 🏰 Noctria Kingdom 御前会議DAG
# ========================================
with DAG(
    dag_id='noctria_kingdom_royal_council_dag',
    default_args=default_args,
    description='市場を観測し、御前会議を開き、王の最終判断を下すための中心的なDAG',
    schedule_interval=timedelta(hours=1), # 1時間ごとに定例会議を開催
    start_date=datetime(2025, 7, 1),
    catchup=False,
    tags=['noctria', 'kingdom', 'royal_council']
) as dag:

    # --- タスク1: 市場データの観測 ---
    def fetch_market_data_task(**kwargs):
        """
        市場の現状を観測し、御前会議に必要な全てのデータを収集する。
        """
        logger = logging.getLogger("MarketObserver")
        logger.info("王国の密偵が市場の観測を開始しました…")
        
        # この関数内で、AurusやNoctusが必要とする全てのデータを取得する
        # MarketDataFetcherを拡張し、テクニカル指標やファンダメンタルズを取得する想定
        
        # テスト用のダミー市場データを作成
        dummy_hist_data = pd.DataFrame({
            'Close': np.random.normal(loc=150, scale=2, size=100)
        })
        dummy_hist_data['returns'] = dummy_hist_data['Close'].pct_change().dropna()

        market_data = {
            "price": 150.50 + np.random.randn(),
            "previous_price": 150.48 + np.random.randn(),
            "volume": np.random.randint(100, 300),
            "volatility": np.random.uniform(0.1, 0.3),
            "sma_5_vs_20_diff": np.random.uniform(-0.1, 0.1),
            "macd_signal_diff": np.random.uniform(-0.05, 0.05),
            "trend_strength": np.random.uniform(0.3, 0.8),
            "trend_prediction": np.random.choice(["bullish", "bearish", "neutral"]),
            "rsi_14": np.random.uniform(30, 70),
            "stoch_k": np.random.uniform(20, 80),
            "momentum": np.random.uniform(0.4, 0.9),
            "bollinger_upper_dist": np.random.uniform(-0.05, 0.05),
            "bollinger_lower_dist": np.random.uniform(-0.05, 0.05),
            "sentiment": np.random.uniform(0.3, 0.9),
            "order_block": np.random.uniform(0.2, 0.8),
            "liquidity_ratio": np.random.uniform(0.8, 1.5),
            "symbol": "USDJPY",
            "interest_rate_diff": 0.05,
            "cpi_change_rate": 0.03,
            "news_sentiment_score": np.random.uniform(0.4, 0.8),
            "spread": np.random.uniform(0.01, 0.02),
            "historical_data": dummy_hist_data.to_json() # DataFrameはJSON文字列に変換
        }
        
        logger.info("市場の観測完了。データを御前会議に提出します。")
        kwargs['ti'].xcom_push(key='market_data', value=market_data)
        return market_data

    # --- タスク2: 御前会議の開催 ---
    def hold_council_task(**kwargs):
        """
        王が五臣を招集し、市場データに基づき最終判断を下す。
        """
        logger = logging.getLogger("RoyalCouncil")
        ti = kwargs['ti']
        market_data_json = ti.xcom_pull(key='market_data', task_ids='fetch_market_data')
        
        if not market_data_json:
            logger.error("市場データが取得できなかったため、会議を中止します。")
            raise ValueError("Market data not found in XComs.")
            
        # XComから受け取ったJSON文字列をDataFrameに戻す
        market_data = market_data_json
        market_data['historical_data'] = pd.read_json(market_data['historical_data'])

        # 王を玉座にお呼びする
        king = KingNoctria()
        
        # 御前会議を開催
        council_report = king.hold_council(market_data)
        
        logger.info(f"会議は終了しました。王の最終判断は『{council_report['final_decision']}』です。")
        kwargs['ti'].xcom_push(key='council_report', value=council_report)
        return council_report

    # --- タスク3: 王命の記録 ---
    def log_decision_task(**kwargs):
        """
        御前会議の結果（王命）を王国の公式記録として保存する。
        """
        logger = logging.getLogger("RoyalScribe")
        ti = kwargs['ti']
        report = ti.xcom_pull(key='council_report', task_ids='hold_council')
        
        if not report:
            logger.warning("記録すべき報告書が存在しませんでした。")
            return

        log_file_path = LOGS_DIR / "kingdom_council_reports" / f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_report.json"
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # DataFrameはJSONにできないため、シリアライズ可能な形式に変換
        if 'assessments' in report and 'noctus_assessment' in report['assessments']:
            if 'historical_data' in report['assessments']['noctus_assessment']:
                del report['assessments']['noctus_assessment']['historical_data']

        with open(log_file_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=4)
            
        logger.info(f"王命を公式記録として書庫に納めました: {log_file_path}")

    # --- タスクの定義 ---
    task_fetch_data = PythonOperator(
        task_id='fetch_market_data',
        python_callable=fetch_market_data_task,
    )

    task_hold_council = PythonOperator(
        task_id='hold_council',
        python_callable=hold_council_task,
    )
    
    task_log_decision = PythonOperator(
        task_id='log_decision',
        python_callable=log_decision_task,
    )

    # --- 依存関係の定義 (王国の統治フロー) ---
    task_fetch_data >> task_hold_council >> task_log_decision
