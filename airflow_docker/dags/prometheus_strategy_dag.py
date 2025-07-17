#!/usr/bin/env python3
# coding: utf-8

"""
🔮 Prometheus Oracle Forecast DAG (v2.0)
- 定期的に未来予測官プロメテウスを起動し、未来予測を生成・保存する。
"""

import logging
import sys
import os
from datetime import datetime, timedelta

from airflow.decorators import dag, task

# --- 王国の基盤モジュールをインポート ---
# ✅ 修正: Airflowが'src'モジュールを見つけられるように、プロジェクトルートをシステムパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.strategies.prometheus_oracle import PrometheusOracle
from src.core.path_config import ORACLE_FORECAST_JSON

# === DAG基本設定 ===
default_args = {
    'owner': 'Prometheus',
    'depends_on_past': False,
    'start_date': datetime(2025, 7, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

@dag(
    dag_id='prometheus_oracle_forecast',
    default_args=default_args,
    description='未来予測官プロメテウスによる定期的な未来予測の儀',
    schedule_interval=timedelta(days=1),  # 1日1回、神託を授かる
    catchup=False,
    tags=['noctria', 'forecasting', 'prometheus'],
)
def prometheus_forecasting_pipeline():
    """
    未来予測官プロメテウスが神託（未来予測）を生成し、王国の書庫に記録するパイプライン。
    """

    @task
    def generate_forecast():
        """未来予測を生成し、JSONファイルとして保存する"""
        logger = logging.getLogger("PrometheusForecastTask")
        logger.info("神託の儀を開始します。未来のビジョンを観測中…")
        
        try:
            oracle = PrometheusOracle()
            # 30日間の未来を予測
            predictions_df = oracle.predict_with_confidence(n_days=30)

            if predictions_df.empty:
                logger.warning("未来のビジョンが不明瞭です。神託は得られませんでした。")
                return

            # 予測結果をファイルに保存
            ORACLE_FORECAST_JSON.parent.mkdir(parents=True, exist_ok=True)
            predictions_df.to_json(ORACLE_FORECAST_JSON, orient="records", force_ascii=False, indent=4)
            logger.info(f"神託を羊皮紙に記し、封印しました: {ORACLE_FORECAST_JSON}")

        except Exception as e:
            logger.error(f"神託の儀の最中に、予期せぬ闇が発生しました: {e}", exc_info=True)
            raise

    # --- パイプラインの定義 ---
    generate_forecast()

# DAGのインスタンス化
prometheus_forecasting_pipeline()
