#!/usr/bin/env python3
# coding: utf-8

"""
🏰 Noctria Kingdom PDCA + Royal Decision 統合DAG
- Optunaによる複数ワーカーのパラメータ探索＆MetaAI/Kingdom昇格＋王の最終意思決定まで一貫自動化
- paramsでworker数/試行回数/スケジュール/王決断時追加処理も柔軟制御
"""

import logging
import sys
import os
from datetime import datetime, timedelta

from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator

# --- Airflowからsrc/配下をimportできるようにパス調整
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- 必要なモジュールをimport ---
from core.path_config import LOGS_DIR
from core.logger import setup_logger
from scripts.optimize_params_with_optuna import optimize_main
from scripts.apply_best_params_to_metaai import apply_best_params_to_metaai
from scripts.apply_best_params_to_kingdom import apply_best_params_to_kingdom

dag_log_path = LOGS_DIR / "dags" / "noctria_kingdom_pdca_dag.log"
logger = setup_logger("NoctriaPDCA_DAG", dag_log_path)

# --- DAG失敗通知（拡張可） ---
def task_failure_alert(context):
    failed_task = context.get('task_instance').task_id
    dag_name = context.get('dag').dag_id
    exec_date = context.get('execution_date')
    log_url = context.get('task_instance').log_url
    message = f"""
    🚨 Airflow Task Failed!
    - DAG: {dag_name}
    - Task: {failed_task}
    - Execution Date: {exec_date}
    - Log URL: {log_url}
    """
    logger.error(message)
    # ここでSlack等にも通知可能

# --- DAG本体 ---
default_args = {
    "owner": "Noctria",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "on_failure_callback": task_failure_alert,
}

with DAG(
    dag_id="noctria_kingdom_pdca_dag",
    description="🏰 Noctria KingdomのPDCA統合DAG（Optuna最適化→MetaAI→Kingdom昇格→王の最終判断）",
    default_args=default_args,
    schedule_interval="@daily",   # paramsでNoneにもできる
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=["noctria", "kingdom", "pdca", "metaai", "royal"],
    params={
        "worker_count": 3,    # 並列ワーカー数
        "n_trials": 100       # Optuna試行回数
    },
) as dag:

    # --- 1. 並列Optuna最適化タスク ---
    def optimize_worker_task(worker_id: int, **kwargs):
        n_trials = kwargs["params"].get("n_trials", 100)
        logger.info(f"🎯 学者{worker_id}が叡智を探求中（試行: {n_trials}）")
        best_params = optimize_main(n_trials=n_trials)
        if not best_params:
            logger.warning(f"worker_{worker_id}: 最適パラメータが得られませんでした")
            return None
        logger.info(f"worker_{worker_id}: ベストパラメータ {best_params}")
        return best_params

    # --- 2. 全ワーカーの結果からベスト選定 ---
    def select_best_params_task(**kwargs):
        ti = kwargs["ti"]
        worker_count = kwargs["params"].get("worker_count", 3)
        results = []
        for i in range(1, worker_count+1):
            params = ti.xcom_pull(task_ids=f"optimize_worker_{i}", key="return_value")
            if params:
                results.append(params)
        if not results:
            logger.warning("全ワーカーの結果が空です")
            return None
        def score_of(p): return p.get("score", 0)
        best = max(results, key=score_of)
        logger.info(f"選定された最良パラメータ: {best}")
        ti.xcom_push(key="best_params", value=best)
        return best

    # --- 3. MetaAIモデルに適用 ---
    def apply_metaai_task(**kwargs):
        ti = kwargs["ti"]
        best_params = ti.xcom_pull(key="best_params", task_ids="select_best_params")
        if not best_params:
            logger.warning("MetaAI適用に使えるベストパラメータがありません")
            return None
        logger.info(f"🧠 MetaAIにベストパラメータ適用開始: {best_params}")
        model_info = apply_best_params_to_metaai(best_params=best_params)
        logger.info(f"MetaAIへの適用完了: {model_info}")
        return model_info

    # --- 4. Kingdom戦略へ昇格 ---
    def apply_kingdom_task(**kwargs):
        ti = kwargs["ti"]
        model_info = ti.xcom_pull(task_ids="apply_best_params_to_metaai", key="return_value")
        if not model_info:
            logger.warning("王国昇格用のモデル情報がありません")
            return None
        logger.info(f"⚔️ 王国戦略昇格開始: {model_info}")
        result = apply_best_params_to_kingdom(model_info=model_info)
        logger.info("王国戦略昇格完了")
        return result

    # --- 5. 王の最終判断タスク（Royal Decision） ---
    def royal_decision_task(**kwargs):
        logger.info("👑 王Noctria: 四臣の報を受け取り、最終決断の儀を執り行います。")
        # ↓ここで本番運用なら遅延import推奨（重い場合）
        try:
            from noctria_ai.noctria import Noctria
            king = Noctria()
            result = king.execute_trade()
            logger.info(f"👑 王の御宣託：{result}")
            return result
        except Exception as e:
            logger.error(f"王決断フェーズで例外発生: {e}")
            return f"王の決断失敗: {e}"

    # --- タスク生成 ---
    workers = [
        PythonOperator(
            task_id=f"optimize_worker_{i}",
            python_callable=optimize_worker_task,
            op_kwargs={"worker_id": i},
        ) for i in range(1, dag.params["worker_count"]+1)
    ]

    select_best = PythonOperator(
        task_id="select_best_params",
        python_callable=select_best_params_task,
    )

    apply_metaai = PythonOperator(
        task_id="apply_best_params_to_metaai",
        python_callable=apply_metaai_task,
    )

    apply_kingdom = PythonOperator(
        task_id="apply_best_params_to_kingdom",
        python_callable=apply_kingdom_task,
    )

    royal_decision = PythonOperator(
        task_id="royal_decision",
        python_callable=royal_decision_task,
    )

    # --- 依存関係 ---
    workers >> select_best >> apply_metaai >> apply_kingdom >> royal_decision
