# airflow_docker/dags/structure_check_dag.py

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import sys
from pathlib import Path

# 🔧 プロジェクトルートを PYTHONPATH に追加（モジュール解決）
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

# ✅ path_config の Lint 関数をインポート
from core.path_config import _lint_path_config

default_args = {
    "owner": "noctria",
    "start_date": datetime(2025, 1, 1),
    "retries": 0,
}

with DAG(
    dag_id="structure_check_dag",
    default_args=default_args,
    schedule_interval=None,  # 手動実行専用
    catchup=False,
    tags=["infra", "lint", "structure"],
    description="📦 Noctria Kingdom パス構造Lintチェック",
) as dag:

    lint_path_config = PythonOperator(
        task_id="lint_path_config",
        python_callable=_lint_path_config,
        dag=dag,
    )
