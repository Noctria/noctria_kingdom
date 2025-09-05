# airflow_docker/dags/veritas_recheck_dag.py
#!/usr/bin/env python3
# coding: utf-8

"""
🔎 Veritas Re-check DAG
- 特定の戦略を個別に再評価する DAG
- GUI/親DAG からの conf を柔軟に受け付ける（後方互換）
    conf 例:
      {
        "strategy": "Aurus_Singularis",     # or "strategy_name"
        "reason": "threshold exceeded",
        "triggered_by": "GUI",              # or "caller"
        "decision_id": "optional-id",       # 無ければ run_id から生成
        "parent_dag": "veritas_recheck_all_dag"  # 任意
      }
- 評価結果は data/pdca_logs/veritas_orders/ に CSV 追記（フォールバック実装あり）
"""

from __future__ import annotations

import csv
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from airflow.decorators import dag, task, get_current_context

# -----------------------------------------------------------------------------
# パス調整: <repo_root> と <repo_root>/src を import path に追加
# -----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# -----------------------------------------------------------------------------
# 評価関数: 本実装が無い環境でも動かせるようフォールバックを用意
# -----------------------------------------------------------------------------
try:
    # 期待: src/core/strategy_evaluator.py で実装済み
    from src.core.strategy_evaluator import evaluate_strategy, log_evaluation_result  # type: ignore
except Exception:
    def evaluate_strategy(strategy_name: str) -> Dict[str, Any]:
        """
        フォールバックのダミー評価。
        実運用では src/core/strategy_evaluator.py を用意してください。
        """
        now = datetime.utcnow().isoformat() + "Z"
        return {
            "strategy": strategy_name,
            "evaluated_at": now,
            "winrate_old": None,
            "winrate_new": 0.0,
            "maxdd_old": None,
            "maxdd_new": 0.0,
            "trades_old": None,
            "trades_new": 0,
            "tag": "recheck",
            "notes": "fallback evaluator",
        }

    def log_evaluation_result(result: Dict[str, Any]) -> None:
        """
        フォールバックのCSV追記。
        実運用では専用ロガーを実装してください。
        """
        log_dir = PROJECT_ROOT / "data" / "pdca_logs" / "veritas_orders"
        log_dir.mkdir(parents=True, exist_ok=True)
        out = log_dir / "rechecks.csv"
        headers = [
            "strategy", "evaluated_at",
            "winrate_old", "winrate_new",
            "maxdd_old", "maxdd_new",
            "trades_old", "trades_new",
            "tag", "notes",
            "trigger_reason", "decision_id", "caller", "parent_dag",
        ]
        write_header = not out.exists()
        with out.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=headers)
            if write_header:
                w.writeheader()
            w.writerow({k: result.get(k) for k in headers})

# -----------------------------------------------------------------------------
# Airflow 設定
# -----------------------------------------------------------------------------
DEFAULT_ARGS = {
    "owner": "VeritasCouncil",
    "depends_on_past": False,
    "retries": 0,
    "start_date": datetime(2025, 7, 1),
}


@dag(
    dag_id="veritas_recheck_dag",
    default_args=DEFAULT_ARGS,
    description="特定の戦略を個別に再評価する（GUI/親DAGからのconf対応）",
    schedule=None,        # Airflow 2.6+ 推奨表記
    catchup=False,
    tags=["noctria", "veritas", "recheck"],
)
def veritas_recheck_pipeline():
    """
    指定戦略を評価し、結果をPDCAログへ記録する。
    conf キーは後方互換で複数名に対応（strategy / strategy_name、caller / triggered_by）。
    """

    @task
    def recheck_and_log_strategy(**context) -> Dict[str, Any]:
        log = logging.getLogger("VeritasRecheckTask")
        ctx = get_current_context()
        dag_run = ctx.get("dag_run")
        conf: Dict[str, Any] = (dag_run.conf or {}) if dag_run else {}

        # --- conf 受け取り（柔軟なキー名に対応）
        strategy: Optional[str] = conf.get("strategy") or conf.get("strategy_name")
        reason: str = conf.get("reason") or "unspecified"
        caller: str = conf.get("triggered_by") or conf.get("caller") or "unknown"
        parent_dag: Optional[str] = conf.get("parent_dag")
        decision_id: Optional[str] = conf.get("decision_id")

        # 無ければ run_id 由来で生成（GUI/親DAG起動時に自動付与）
        if not decision_id:
            run_id = getattr(dag_run, "run_id", "manual__unknown")
            decision_id = f"recheck:{strategy or 'unknown'}:{run_id}"

        # --- バリデーション
        if not strategy:
            msg = "このDAGは手動/親DAG経由の実行専用です。conf.strategy（または strategy_name）が必須です。"
            log.error(msg)
            raise ValueError(msg)

        log.info(
            "[decision_id:%s] 再評価受理: strategy=%s reason=%s caller=%s parent_dag=%s",
            decision_id, strategy, reason, caller, parent_dag,
        )

        # --- 再評価
        try:
            result = evaluate_strategy(strategy)
            # 追記情報
            result["trigger_reason"] = reason
            result["decision_id"] = decision_id
            result["caller"] = caller
            result["parent_dag"] = parent_dag

            # --- ログ記録
            log_evaluation_result(result)

            log.info("[decision_id:%s] 再評価・記録完了: %s", decision_id, strategy)
            return result

        except FileNotFoundError as e:
            log.error("[decision_id:%s] 戦略ファイル未検出: %s", decision_id, e)
            raise
        except Exception as e:
            log.error("[decision_id:%s] 再評価中エラー: %s", decision_id, e, exc_info=True)
            raise

    recheck_and_log_strategy()


veritas_recheck_pipeline()
