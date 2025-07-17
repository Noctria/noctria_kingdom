#!/usr/bin/env python3
# coding: utf-8

"""
🔁 Veritas PDCA Loop DAG (v2.1)
- 戦略の「生成(Plan)」「評価(Do/Check)」「採用戦略のPush(Act)」という
- PDCAサイクルを自動で実行するためのマスターDAG。
"""

import logging
import sys
import os
from datetime import datetime

from airflow.decorators import dag, task

# --- 王国の基盤モジュールをインポート ---
# ✅ 修正: Airflowが'src'モジュールを見つけられるように、プロジェクトルートをシステムパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ✅ 修正: 各スクリプトからメインの処理関数をインポート
from src.veritas.veritas_generate_strategy import main as generate_main
from src.veritas.evaluate_veritas import main as evaluate_main
from src.scripts.github_push_adopted_strategies import main as push_main

# === DAG内ヘルパー関数 ===
def log_pdca_step(phase: str, status: str, message: str):
    """PDCAの各ステップの状況をログに出力する"""
    logging.info(f"PDCA LOG - [{phase}] [{status}] :: {message}")

# === DAG基本設定 ===
default_args = {
    'owner': 'VeritasCouncil',
    'depends_on_past': False,
    'start_date': datetime(2025, 7, 1),
    'retries': 0,
}

@dag(
    dag_id="veritas_pdca_loop",
    default_args=default_args,
    description="Veritasによる自動戦略PDCAループ",
    schedule_interval=None,
    catchup=False,
    tags=['veritas', 'pdca', 'master'],
)
def veritas_pdca_pipeline():
    """
    Veritasの戦略生成からPushまでの一連のPDCAプロセスを管理するパイプライン。
    """

    @task
    def generate_strategy():
        """Plan: 新たな戦略を生成する"""
        log_pdca_step("Plan", "Start", "戦略生成の儀を開始します。")
        try:
            generate_main()
            log_pdca_step("Plan", "Success", "新たな戦略の創出に成功しました。")
        except Exception as e:
            log_pdca_step("Plan", "Failure", f"戦略生成に失敗しました: {e}")
            raise

    @task
    def evaluate_generated_strategy():
        """Do & Check: 生成された戦略を評価する"""
        log_pdca_step("Check", "Start", "戦略評価の儀を開始します。")
        try:
            evaluate_main()
            log_pdca_step("Check", "Success", "戦略の真価を見極めました。")
        except Exception as e:
            log_pdca_step("Check", "Failure", f"戦略評価に失敗しました: {e}")
            raise

    @task
    def push_adopted_strategy():
        """Act: 採用基準を満たした戦略を正式に記録（Push）する"""
        log_pdca_step("Act", "Start", "採用されし戦略の公式記録を開始します。")
        try:
            push_main()
            log_pdca_step("Act", "Success", "採用戦略の記録が完了しました。")
        except Exception as e:
            log_pdca_step("Act", "Failure", f"採用戦略の記録に失敗しました: {e}")
            raise

    # --- パイプラインの定義 (PDCAのワークフロー) ---
    generate_task = generate_strategy()
    evaluate_task = evaluate_generated_strategy()
    push_task = push_adopted_strategy()

    generate_task >> evaluate_task >> push_task

# DAGのインスタンス化
veritas_pdca_pipeline()
