#!/usr/bin/env python3
# coding: utf-8

"""
🔎 Veritas Re-check DAG (v2.0)
- 特定の戦略を個別に再評価するためのDAG。
- AirflowのUIから手動でトリガーし、`dag_run.conf`経由で戦略名を指定することを想定。
"""

import logging
import sys
import os
from datetime import datetime
from typing import Dict, Any

from airflow.decorators import dag, task

# --- 王国の基盤モジュールをインポート ---
# ✅ Airflowが'src'モジュールを見つけられるように、プロジェクトルートをsys.pathに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ✅ 評価とログ保存の関数を正しくインポート
from src.core.strategy_evaluator import evaluate_strategy, log_evaluation_result

# === DAG基本設定 ===
default_args = {
    'owner': 'VeritasCouncil',
    'depends_on_past': False,
    'start_date': datetime(2025, 7, 1),
    'retries': 0,
}

@dag(
    dag_id="veritas_recheck_dag",
    default_args=default_args,
    description="特定の戦略を個別に再評価する",
    schedule_interval=None,
    catchup=False,
    tags=["veritas", "recheck"],
)
def veritas_recheck_pipeline():
    """
    特定の戦略を指定して再評価し、その結果を記録するパイプライン。
    """

    @task
    def recheck_and_log_strategy(**context) -> Dict[str, Any]:
        """
        DAG実行時に渡された戦略名を元に、再評価とログ記録を行う。
        """
        logger = logging.getLogger("VeritasRecheckTask")
        dag_run = context.get("dag_run")

        # DAG実行時に`conf`で戦略名が渡されているかチェック
        if not dag_run or not dag_run.conf or "strategy_name" not in dag_run.conf:
            error_msg = "このDAGは手動実行専用です。'strategy_name'をJSON形式で指定してください。"
            logger.error(error_msg)
            raise ValueError(error_msg)

        strategy_name = dag_run.conf.get("strategy_name")
        logger.info(f"戦略『{strategy_name}』の再評価命令を受理しました。")

        try:
            # 1. 戦略を評価
            evaluation_result = evaluate_strategy(strategy_name)

            # 2. 評価結果をログに記録
            log_evaluation_result(evaluation_result)

            logger.info(f"戦略『{strategy_name}』の再評価と記録が完了しました。")
            return evaluation_result

        except FileNotFoundError as e:
            logger.error(f"再評価エラー: 対象の戦略ファイルが見つかりません。詳細: {e}")
            raise
        except Exception as e:
            logger.error(f"再評価中に予期せぬエラーが発生しました: {e}", exc_info=True)
            raise

    # --- パイプラインの定義 ---
    recheck_and_log_strategy()

# DAGのインスタンス化
veritas_recheck_pipeline()
