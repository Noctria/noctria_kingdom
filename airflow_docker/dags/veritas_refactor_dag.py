from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
from pathlib import Path
import os

# 🔧 ベースパス（Docker対応）: config.py不要で環境変数から取得
BASE_DIR = Path(os.getenv("TARGET_PROJECT_ROOT", "/noctria_kingdom")).resolve()

# 📂 統一パス定義
TOOLS_DIR = BASE_DIR / "tools"
SCRIPTS_DIR = BASE_DIR / "scripts"
TESTS_DIR = BASE_DIR / "tests"

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

    scan_structure = BashOperator(
        task_id="scan_structure",
        bash_command=f"python3 {TOOLS_DIR / 'scan_refactor_plan.py'}",
    )

    pause_for_review = EmptyOperator(
        task_id="pause_for_review",
        doc_md="""
        ### 🧠 手動レビュー推奨ポイント
        - Airflow UIで構造スキャン結果を確認してください
        - 問題なければ手動で次に進めてください
        """,
    )

    dry_run_refactor = BashOperator(
        task_id="dry_run_refactor",
        bash_command=f"python3 {TOOLS_DIR / 'apply_refactor_plan.py'} --dry-run",
    )

    run_tests = BashOperator(
        task_id="run_tests",
        bash_command=f"pytest {TESTS_DIR}",
    )

    apply_refactor = BashOperator(
        task_id="apply_refactor",
        bash_command=f"python3 {TOOLS_DIR / 'apply_refactor_plan.py'}",
    )

    push_to_github = BashOperator(
        task_id="push_to_github",
        bash_command=f"python3 {SCRIPTS_DIR / 'github_push.py'}",
        trigger_rule=TriggerRule.ALL_SUCCESS,
    )

    end = EmptyOperator(task_id="end")

    # DAG依存関係の構築
    start >> scan_structure >> pause_for_review
    pause_for_review >> dry_run_refactor >> run_tests >> apply_refactor >> push_to_github >> end
