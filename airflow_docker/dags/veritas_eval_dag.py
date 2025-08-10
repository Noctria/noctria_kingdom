#!/usr/bin/env python3
# coding: utf-8

"""
✅ Veritas Evaluation Pipeline DAG (理想型・王API決裁ID対応)
- Veritasが生成した戦略を動的に評価し、採用/不採用を判断し、その結果を記録する。
- conf（理由, decision_id, caller等）を全タスクで受信・記録可能
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import logging

from airflow.decorators import dag, task
from airflow.operators.python import get_current_context

# --- パス調整
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.path_config import STRATEGIES_VERITAS_GENERATED_DIR, ACT_LOG_DIR
from src.core.strategy_evaluator import evaluate_strategy, log_evaluation_result

default_args = {
    'owner': 'VeritasCouncil',
    'depends_on_past': False,
    'start_date': datetime(2025, 7, 1),
    'retries': 0,
}

@dag(
    dag_id='veritas_evaluation_pipeline',
    default_args=default_args,
    description='Veritas生成戦略の評価・採用判定DAG（decision_id等対応版）',
    schedule=None,
    catchup=False,
    tags=['veritas', 'evaluation', 'pdca'],
)
def veritas_evaluation_pipeline():
    """
    Veritasが生成した戦略を動的に評価し、採用するパイプライン
    conf（理由, decision_id, caller等）も全タスクで受信・記録可能
    """

    @task
    def get_strategies_to_evaluate() -> List[str]:
        ctx = get_current_context()
        conf = ctx["dag_run"].conf if ctx.get("dag_run") and ctx["dag_run"].conf else {}
        decision_id = conf.get("decision_id", "NO_DECISION_ID")
        reason = conf.get("reason", "理由未指定")
        caller = conf.get("caller", "unknown")
        logging.info(f"【Veritas評価タスク開始】[decision_id:{decision_id}]【発令理由】{reason}【呼出元】{caller}")

        if not STRATEGIES_VERITAS_GENERATED_DIR.exists():
            logging.warning(f"⚠️ 戦略生成ディレクトリが存在しません: {STRATEGIES_VERITAS_GENERATED_DIR}")
            return []
        new_strategies = [
            f.stem for f in STRATEGIES_VERITAS_GENERATED_DIR.iterdir()
            if f.is_file() and f.suffix == '.py' and not f.name.startswith('__')
        ]
        logging.info(f"🔍 [decision_id:{decision_id}] {len(new_strategies)}件の新しい戦略を評価対象として発見しました。")
        return new_strategies

    @task
    def evaluate_one_strategy(strategy_id: str) -> Dict[str, Any]:
        ctx = get_current_context()
        conf = ctx["dag_run"].conf if ctx.get("dag_run") and ctx["dag_run"].conf else {}
        decision_id = conf.get("decision_id", "NO_DECISION_ID")
        reason = conf.get("reason", "理由未指定")
        caller = conf.get("caller", "unknown")
        logging.info(f"📊 [decision_id:{decision_id}] 評価開始: {strategy_id}【発令理由】{reason}【呼出元】{caller}")
        try:
            result = evaluate_strategy(strategy_id)
            result["status"] = "ok"
            result["trigger_reason"] = reason
            result["decision_id"] = decision_id
            result["caller"] = caller
        except Exception as e:
            logging.error(f"🚫 [decision_id:{decision_id}] 評価エラー: {strategy_id} ➜ {e}", exc_info=True)
            result = {
                "strategy": strategy_id,
                "status": "error",
                "error_message": str(e),
                "trigger_reason": reason,
                "decision_id": decision_id,
                "caller": caller
            }
        return result

    @task
    def log_all_results(evaluation_results: List[Dict]):
        ctx = get_current_context()
        conf = ctx["dag_run"].conf if ctx.get("dag_run") and ctx["dag_run"].conf else {}
        decision_id = conf.get("decision_id", "NO_DECISION_ID")
        reason = conf.get("reason", "理由未指定")
        caller = conf.get("caller", "unknown")
        logging.info(f"📝 [decision_id:{decision_id}] {len(evaluation_results) if evaluation_results else 0}件の評価結果を記録…【発令理由】{reason}【呼出元】{caller}")
        if not evaluation_results:
            logging.info("評価対象の戦略がなかったため、ログ記録をスキップします。")
            return

        for result in evaluation_results:
            if result.get("status") == "ok":
                # 統治ID/呼び出し元を結果に明示的に記録
                result["decision_id"] = decision_id
                result["caller"] = caller
                log_evaluation_result(result)
        logging.info(f"✅ [decision_id:{decision_id}] 全ての評価記録の保存が完了しました。")

    strategy_ids = get_strategies_to_evaluate()
    evaluated_results = evaluate_one_strategy.expand(strategy_id=strategy_ids)
    log_all_results(evaluation_results=evaluated_results)

veritas_evaluation_pipeline()
