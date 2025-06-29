from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.dates import days_ago

default_args = {
    "owner": "noctria",
    "start_date": days_ago(1),
}

with DAG(
    dag_id="veritas_refactor_dag",
    default_args=default_args,
    schedule_interval=None,
    catchup=False,
    description="段階的にVeritas構造を自動リファクタリングするDAG",
) as dag:

    start = EmptyOperator(task_id="start")

    scan_structure = BashOperator(
        task_id="scan_structure",
        bash_command="python3 /noctria_kingdom/tools/scan_refactor_plan.py",
    )

    pause_for_review = EmptyOperator(
        task_id="pause_for_review",
        doc_md="### 📌 Airflow UI上で一時停止して構造レビューしてください。通過したら次へ。",
    )

    dry_run_refactor = BashOperator(
        task_id="dry_run_refactor",
        bash_command="python3 /noctria_kingdom/tools/apply_refactor_plan.py --dry-run",
    )

    run_tests = BashOperator(
        task_id="run_tests",
        bash_command="pytest /noctria_kingdom/tests/",
    )

    apply_refactor = BashOperator(
        task_id="apply_refactor",
        bash_command="python3 /noctria_kingdom/tools/apply_refactor_plan.py",
    )

    push_to_github = BashOperator(
        task_id="push_to_github",
        bash_command="python3 /noctria_kingdom/scripts/github_push.py",
    )

    end = EmptyOperator(task_id="end")

    # DAG依存関係の構築
    start >> scan_structure >> pause_for_review
    pause_for_review >> dry_run_refactor >> run_tests >> apply_refactor >> push_to_github >> end
