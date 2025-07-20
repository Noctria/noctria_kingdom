#!/usr/bin/env python3
# coding: utf-8

"""
🔁 Veritas PDCA Loop DAG (v2.2/統合版)
- Veritasによる「戦略生成」「評価」「Push」のPDCAサイクルを自動化
- マスターDAG機能（master_dagの意図も包含）一本化
"""

import logging
import sys
import os
from datetime import datetime

from airflow.decorators import dag, task

# --- Airflowが'src'モジュールを見つけられるようにプロジェクトルートをパス追加 ---
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Veritas戦略関連スクリプトのインポート ---
from src.veritas.veritas_generate_strategy import main as generate_main
from src.veritas.evaluate_veritas import main as evaluate_main
from src.scripts.github_push_adopted_strategies import main as push_main

# === DAG内ヘルパー関数 ===
def log_pdca_step(phase: str, status: str, message: str):
    """PDCAの各ステップの状況をAirflowログに出力"""
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
    description="Veritasによる戦略生成・評価・Push一貫PDCAマスターDAG",
    schedule_interval=None,  # 手動実行 or 外部トリガのみ
    catchup=False,
    tags=['veritas', 'pdca', 'master'],
)
def veritas_pdca_pipeline():
    """
    Veritasの戦略創出から公式記録（Push）までのPDCA全体を統合管理。
    今後「詳細ログ化」「フェーズ分岐」「複数戦略バッチ」等の拡張もこのDAGに集約可能。
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
        """Do/Check: 生成された戦略を評価する"""
        log_pdca_step("Check", "Start", "戦略評価の儀を開始します。")
        try:
            evaluate_main()
            log_pdca_step("Check", "Success", "戦略の真価を見極めました。")
        except Exception as e:
            log_pdca_step("Check", "Failure", f"戦略評価に失敗しました: {e}")
            raise

    @task
    def push_adopted_strategy():
        """Act: 採用基準を満たした戦略を公式記録（Push）"""
        log_pdca_step("Act", "Start", "採用戦略の公式記録（Push）を開始します。")
        try:
            push_main()
            log_pdca_step("Act", "Success", "採用戦略の記録が完了しました。")
        except Exception as e:
            log_pdca_step("Act", "Failure", f"採用戦略の記録に失敗しました: {e}")
            raise

    # --- PDCAワークフロー定義 ---
    g = generate_strategy()
    e = evaluate_generated_strategy()
    p = push_adopted_strategy()

    g >> e >> p

# DAGのインスタンス化（Airflowが認識）
veritas_pdca_pipeline()
