#!/usr/bin/env python3
# coding: utf-8

"""
🔎 Veritas Re-check DAG (v2.1 conf対応)
- 特定の戦略を個別に再評価するためのDAG。
- AirflowのUI/REST/GUIから手動でトリガーし、`dag_run.conf`経由で戦略名・理由を指定できる設計。
"""

import logging
import sys
import os
from datetime import datetime
from typing import Dict, Any

from airflow.decorators import dag, task, get_current_context

# --- パス調整
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.strategy_evaluator import evaluate_strategy, log_evaluation_result

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
    発令理由（conf["reason"]）も記録
    """

    @task
    def recheck_and_log_strategy(**context) -> Dict[str, Any]:
        logger = logging.getLogger("VeritasRecheckTask")
        # Airflow TaskFlowではget_current_context()が最も確実
        from airflow.decorators import get_current_context
        ctx = get_current_context()
        dag_run = ctx.get("dag_run")
        conf = dag_run.conf if dag_run and dag_run.conf else {}

        # 必須: 戦略名、任意: 理由
        strategy_name = conf.get("strategy_name")
        reason = conf.get("reason", "理由未指定")

        if not strategy_name:
            error_msg = "このDAGは手動実行専用です。'strategy_name'をJSON形式で指定してください。"
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(f"戦略『{strategy_name}』の再評価命令を受理しました。（理由: {reason}）")

        try:
            # 1. 戦略を評価
            evaluation_result = evaluate_strategy(strategy_name)
            evaluation_result["trigger_reason"] = reason  # 評価結果にも理由を追加

            # 2. 評価結果をログに記録
            log_evaluation_result(evaluation_result)

            logger.info(f"戦略『{strategy_name}』の再評価と記録が完了しました。（理由: {reason}）")
            return evaluation_result

        except FileNotFoundError as e:
            logger.error(f"再評価エラー: 対象の戦略ファイルが見つかりません。詳細: {e}")
            raise
        except Exception as e:
            logger.error(f"再評価中に予期せぬエラーが発生しました: {e}", exc_info=True)
            raise

    recheck_and_log_strategy()

veritas_recheck_pipeline()
