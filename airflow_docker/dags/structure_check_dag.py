from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import sys
from pathlib import Path

# 🔧 core/path_config.py をモジュールとして読み込む
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from core.path_config import _lint_path_config  # ✅ Lint関数を直接呼ぶ

with DAG(
    dag_id="structure_check_dag",
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,  # 手動実行のみ
    catchup=False,
    tags=["lint", "infra", "structure"]
) as dag:

    path_lint_task = PythonOperator(
        task_id="lint_path_config",
        python_callable=_lint_path_config
    )
