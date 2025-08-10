#!/usr/bin/env python3
# coding: utf-8

"""
⚔️ Veritas to EA Order DAG (v2.0)
- Veritasが生成・評価した戦略から、最終的にEA（自動売買プログラム）が読み込む
- 命令JSONファイルを生成するまでの一連のプロセスを自動化する。
"""

import logging
import sys
import os
from datetime import datetime, timedelta

from airflow.decorators import dag, task

# --- 王国の基盤モジュールをインポート ---
# ✅ 修正: Airflowが'src'モジュールを見つけられるように、プロジェクトルートをシステムパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ✅ 修正: 各スクリプトからメインの処理関数をインポート
# 存在しないモジュールを削除し、必要なものを正しくインポート
from src.veritas.evaluate_veritas import main as evaluate_main
# from src.veritas.promote_accepted_strategies import main as promote_main # このスクリプトは存在しない可能性
from src.execution.generate_order_json import main as generate_order_main

# === DAG基本設定 ===
default_args = {
    "owner": "VeritasCouncil",
    "depends_on_past": False,
    "start_date": datetime(2025, 7, 1),
    "retries": 1,
    "retry_delay": timedelta(minutes=3),
}

@dag(
    dag_id="veritas_to_order_pipeline",
    default_args=default_args,
    description="Veritas戦略評価からEA命令JSON生成までの完全自動化パイプライン",
    schedule=None,  # 手動実行を基本とする
    catchup=False,
    tags=["veritas", "pdca", "auto-ea"],
)
def veritas_to_order_pipeline():
    """
    戦略の評価、採用、そしてEAへの命令書作成までを統括する。
    """

    @task
    def evaluate_strategies_task():
        """Check: 生成された全戦略の真価を問う"""
        logging.info("評価の儀を開始します。")
        try:
            evaluate_main()
        except Exception as e:
            logging.error(f"評価の儀で失敗しました: {e}", exc_info=True)
            raise

    @task
    def generate_order_json_task():
        """Do: 採用された戦略に基づき、EAへの命令書を作成する"""
        logging.info("王の最終承認に基づき、EAへの命令書を作成します。")
        try:
            # この関数は内部で評価ログを読み、採用された戦略のみを対象とする
            generate_order_main()
        except Exception as e:
            logging.error(f"命令書の作成に失敗しました: {e}", exc_info=True)
            raise

    # --- パイプラインの定義 (評価 → 命令書作成) ---
    evaluate_task = evaluate_strategies_task()
    generate_order_task = generate_order_json_task()

    evaluate_task >> generate_order_task

# DAGのインスタンス化
veritas_to_order_pipeline()
