#!/usr/bin/env python3
# coding: utf-8

"""
🔎 Veritas Re-check DAG (理想型)
- 特定の戦略を個別に再評価するためのDAG。
- confでstrategy_name, decision_id, caller, reason等を必須受信
"""

import logging
import sys
import os
from datetime import datetime
from typing import Dict, Any

from airflow.decorators import dag, task
from airflow.operators.python import get_current_context

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
    description="特定の戦略を個別に再評価する（統治ID・呼出元必須）",
    schedule_interval=None,
    catchup=False,
    tags=["veritas", "recheck"],
)
def veritas_recheck_pipeline():
    """
    特定の戦略を指定して再評価し、その結果を記録するパイプライン。
    decision_id, caller, reason等も必ず記録
    """

    @task
    def recheck_and_log_strategy(**context) -> Dict[str, Any]:
        logger = logging.getLogger("VeritasRecheckTask")
        from airflow.decorators import get_current_context
        ctx = get_current_context()
        dag_run = ctx.get("dag_run")
        conf = dag_run.conf if dag_run and dag_run.conf else {}

        strategy_name = conf.get("strategy_name")
        decision_id = conf.get("decision_id", "NO_DECISION_ID")
        reason = conf.get("reason", "理由未指定")
        caller = conf.get("caller", "unknown")

        # バリデーション
        if not strategy_name:
            error_msg = "このDAGはNoctria王API経由の手動実行専用です。'strategy_name'をJSON形式で指定してください。"
            logger.error(error_msg)
            raise ValueError(error_msg)
        if decision_id == "NO_DECISION_ID":
            logger.error("統治ID（decision_id）が指定されていません！王API経由のみ許可")
            raise ValueError("decision_idが必要です。Noctria王経由でのみDAG起動が許可されます。")

        logger.info(f"[decision_id:{decision_id}] 戦略『{strategy_name}』の再評価命令を受理。（理由: {reason}／呼出元: {caller}）")

        try:
            # 1. 戦略を評価
            evaluation_result = evaluate_strategy(strategy_name)
            evaluation_result["trigger_reason"] = reason
            evaluation_result["decision_id"] = decision_id
            evaluation_result["caller"] = caller

            # 2. 評価結果をログに記録
            log_evaluation_result(evaluation_result)

            logger.info(f"[decision_id:{decision_id}] 戦略『{strategy_name}』の再評価・記録完了。（理由: {reason}／呼出元: {caller}）")
            return evaluation_result

        except FileNotFoundError as e:
            logger.error(f"[decision_id:{decision_id}] 再評価エラー: 対象戦略ファイルが見つかりません。詳細: {e}")
            raise
        except Exception as e:
            logger.error(f"[decision_id:{decision_id}] 再評価中に予期せぬエラー発生: {e}", exc_info=True)
            raise

    recheck_and_log_strategy()

veritas_recheck_pipeline()
