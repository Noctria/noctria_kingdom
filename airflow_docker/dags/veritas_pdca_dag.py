#!/usr/bin/env python3
# coding: utf-8

"""
🔁 Veritas PDCA Loop DAG (v2.3/ログ強化・リトライ対応版)
- Veritasによる「戦略生成」「評価」「Push」のPDCAサイクルを自動化
- 失敗時にリトライ、例外内容詳細ログを出力
"""

import logging
import sys
import os
from datetime import datetime, timedelta

from airflow.decorators import dag, task
from airflow.utils.email import send_email

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

def send_failure_email(context):
    """失敗時に通知メールを送信する（Airflowのon_failure_callback用）"""
    dag_run = context.get('dag_run')
    task_instance = context.get('task_instance')
    subject = f"【Airflow DAG失敗通知】{dag_run.dag_id} - task: {task_instance.task_id}"
    body = f"""
    DAG: {dag_run.dag_id}
    タスク: {task_instance.task_id}
    実行日時: {dag_run.execution_date}
    ログURL: {task_instance.log_url}

    エラー詳細:
    {context.get('exception')}
    """
    # メール送信 (Airflow設定でSMTPが必要)
    send_email(to=["your_email@example.com"], subject=subject, html_content=body)

# === DAG基本設定（リトライ含む）===
default_args = {
    'owner': 'VeritasCouncil',
    'depends_on_past': False,
    'start_date': datetime(2025, 7, 1),
    'retries': 3,                       # 3回までリトライ
    'retry_delay': timedelta(minutes=5),  # 5分間隔でリトライ
    'on_failure_callback': send_failure_email,  # 失敗通知コールバック
    'email_on_failure': False,          # Airflow標準メールはOFF（カスタム利用）
}

@dag(
    dag_id="veritas_pdca_loop_v2",
    default_args=default_args,
    description="Veritas PDCA Loop DAG（リトライ＆ログ強化版）",
    schedule=None,  # 手動実行 or 外部トリガのみ
    catchup=False,
    tags=['veritas', 'pdca', 'master'],
)
def veritas_pdca_pipeline():
    """
    Veritasの戦略創出からPushまでのPDCA全体を統合管理。
    リトライ対応・失敗通知・ログ強化済み。
    """

    @task(retries=2, retry_delay=timedelta(minutes=3))
    def generate_strategy():
        """Plan: 新たな戦略を生成する"""
        log_pdca_step("Plan", "Start", "戦略生成の儀を開始します。")
        try:
            generate_main()
            log_pdca_step("Plan", "Success", "新たな戦略の創出に成功しました。")
        except Exception as e:
            log_pdca_step("Plan", "Failure", f"戦略生成に失敗しました: {e}")
            raise

    @task(retries=2, retry_delay=timedelta(minutes=3))
    def evaluate_generated_strategy():
        """Do/Check: 生成された戦略を評価する"""
        log_pdca_step("Check", "Start", "戦略評価の儀を開始します。")
        try:
            evaluate_main()
            log_pdca_step("Check", "Success", "戦略の真価を見極めました。")
        except Exception as e:
            log_pdca_step("Check", "Failure", f"戦略評価に失敗しました: {e}")
            raise

    @task(retries=2, retry_delay=timedelta(minutes=3))
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
