#!/usr/bin/env python3
# coding: utf-8

"""
👑 Veritas Master DAG (v2.0)
- Veritasによる「戦略生成」「評価」「Push」の一連のプロセスを統括するマスターDAG。
- 王国の自己進化サイクルそのものを司る。
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
from src.scripts.log_pdca_result import log_pdca_step

# === DAG基本設定 ===
default_args = {
    'owner': 'VeritasCouncil',
    'depends_on_past': False,
    'start_date': datetime(2025, 7, 1),
    'retries': 0,
}

@dag(
    dag_id="veritas_master_pipeline",
    default_args=default_args,
    description="Veritasによる戦略の生成・評価・Pushを統括するマスターパイプライン",
    schedule_interval=None,  # 手動実行を基本とする
    catchup=False,
    tags=['veritas', 'master', 'pipeline'],
)
def veritas_master_pipeline():
    """
    Veritasの戦略創出から公式記録までの全プロセスを管理する。
    """

    @task
    def generate_strategy_task():
        """Plan: 新たな戦略を生成する"""
        log_pdca_step("Master-Plan", "Start", "マスターパイプラインより、戦略生成の儀を開始します。")
        try:
            generate_main()
            log_pdca_step("Master-Plan", "Success", "新たな戦略の創出に成功しました。")
        except Exception as e:
            log_pdca_step("Master-Plan", "Failure", f"戦略生成に失敗しました: {e}")
            raise

    @task
    def evaluate_strategy_task():
        """Do & Check: 生成された戦略を評価する"""
        log_pdca_step("Master-Check", "Start", "戦略評価の儀を開始します。")
        try:
            evaluate_main()
            log_pdca_step("Master-Check", "Success", "戦略の真価を見極めました。")
        except Exception as e:
            log_pdca_step("Master-Check", "Failure", f"戦略評価に失敗しました: {e}")
            raise

    @task
    def push_strategy_task():
        """Act: 採用基準を満たした戦略を正式に記録（Push）する"""
        log_pdca_step("Master-Act", "Start", "採用されし戦略の公式記録を開始します。")
        try:
            # このスクリプトは、評価ログを読み、採用されたものだけをPushするロジックを持つ
            push_main()
            log_pdca_step("Master-Act", "Success", "採用戦略の記録が完了しました。")
        except Exception as e:
            log_pdca_step("Master-Act", "Failure", f"採用戦略の記録に失敗しました: {e}")
            raise

    # --- パイプラインの定義 (生成 → 評価 → Push) ---
    generate_task = generate_strategy_task()
    evaluate_task = evaluate_generated_strategy()
    push_task = push_adopted_strategy()

    generate_task >> evaluate_task >> push_task

# DAGのインスタンス化
veritas_master_pipeline()
