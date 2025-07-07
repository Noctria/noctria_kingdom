#!/usr/bin/env python3
# coding: utf-8

"""
📊 Airflow DAG: 再評価処理（recheck）
- 外部から strategy_id を conf で受け取り、評価スクリプトを実行
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import datetime
import subprocess

def run_recheck(**context):
    """
    🎯 指定された strategy_id を使って再評価スクリプトを実行
    """
    conf = context["dag_run"].conf or {}
    strategy_id = conf.get("strategy_id")
    if not strategy_id:
        raise ValueError("strategy_id が指定されていません")

    print(f"🔁 再評価対象: {strategy_id}")

    # 評価スクリプトを実行
    result = subprocess.run(
        ["python3", "scripts/recheck_runner.py", strategy_id],
        capture_output=True,
        text=True,
    )

    print("📤 STDOUT:")
    print(result.stdout)
    print("📥 STDERR:")
    print(result.stderr)

    if result.returncode != 0:
        raise RuntimeError(f"再評価スクリプトが失敗しました: {result.stderr}")

# ✅ DAG定義（明示的に dag 変数を残すこと）
default_args = {
    "owner": "airflow",
}

dag = DAG(
    dag_id="recheck_dag",
    description="Noctria Kingdom - 戦略再評価処理（recheck）",
    default_args=default_args,
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["pdca", "recheck"],
)

# ✅ タスク定義
recheck_task = PythonOperator(
    task_id="run_recheck",
    python_callable=run_recheck,
    dag=dag,
)
