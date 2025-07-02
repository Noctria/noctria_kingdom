from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule

# パス定義（path_config.py 経由）
from core.path_config import TOOLS_DIR, SCRIPTS_DIR, TESTS_DIR

import sys
import os

# PythonPath に BASE_DIR を追加（Airflow Worker 上でもimport解決）
BASE_DIR = str(TOOLS_DIR.parent)
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

default_args = {
    "owner": "noctria",
    "start_date": days_ago(1),
}

with DAG(
    dag_id="veritas_refactor_dag",
    default_args=default_args,
    schedule_interval=None,
    catchup=False,
    description="段階的にVeritas構造を自動リファクタリングするDAG（v2.0準拠）",
) as dag:

    start = EmptyOperator(task_id="start")

    def run_scan_structure():
        from tools import scan_refactor_plan
        scan_refactor_plan.main()

    scan_structure = PythonOperator(
        task_id="scan_structure",
        python_callable=run_scan_structure,
    )

    pause_for_review = EmptyOperator(
        task_id="pause_for_review",
        doc_md="""
        ### 🧠 手動レビュー推奨ポイント
        - Airflow UIで構造スキャン結果を確認してください
        - 問題なければ手動で次に進めてください
        """,
    )

    def run_dry_run_refactor():
        from tools import apply_refactor_plan
        apply_refactor_plan.main(dry_run=True)

    dry_run_refactor = PythonOperator(
        task_id="dry_run_refactor",
        python_callable=run_dry_run_refactor,
    )

    def run_tests():
        import pytest
        return pytest.main([str(TESTS_DIR)])

    run_tests_op = PythonOperator(
        task_id="run_tests",
        python_callable=run_tests,
    )

    def run_apply_refactor():
        from tools import apply_refactor_plan
        apply_refactor_plan.main(dry_run=False)

    apply_refactor = PythonOperator(
        task_id="apply_refactor",
        python_callable=run_apply_refactor,
    )

    def push_to_github():
        from scripts import github_push
        github_push.main()

    push_to_github_op = PythonOperator(
        task_id="push_to_github",
        python_callable=push_to_github,
        trigger_rule=TriggerRule.ALL_SUCCESS,
    )

    end = EmptyOperator(task_id="end")

    # DAG依存関係の構築
    start >> scan_structure >> pause_for_review
    pause_for_review >> dry_run_refactor >> run_tests_op >> apply_refactor >> push_to_github_op >> end
