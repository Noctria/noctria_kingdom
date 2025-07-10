from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from pathlib import Path
import json
import os
import random

from core.path_config import STRATEGIES_DIR, ACT_LOG_DIR

def recheck_strategy(**context):
    dag_run = context.get("dag_run")
    if not dag_run or not dag_run.conf:
        raise ValueError("DAG must be triggered with a config including 'strategy_name'")

    strategy_name = dag_run.conf.get("strategy_name")
    if not strategy_name:
        raise ValueError("strategy_name is required in dag_run.conf")

    strategy_path = STRATEGIES_DIR / "veritas_generated" / f"{strategy_name}.json"
    if not strategy_path.exists():
        raise FileNotFoundError(f"Strategy file not found: {strategy_path}")

    with open(strategy_path, "r", encoding="utf-8") as f:
        strategy_data = json.load(f)

    # 疑似再スコア（安定のためseed固定）
    seed = sum(ord(c) for c in strategy_name)
    random.seed(seed)
    new_win_rate = round(50 + random.uniform(0, 50), 2)
    new_max_dd = round(random.uniform(5, 30), 2)

    result = {
        "strategy": strategy_name,
        "timestamp": datetime.now().isoformat(),
        "win_rate": new_win_rate,
        "max_drawdown": new_max_dd,
        "source": "recheck_dag",
    }

    ACT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    output_path = ACT_LOG_DIR / f"recheck_{strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # ✅ 他タスクにXComで返す
    return result

# ===========================
# DAG定義
# ===========================
default_args = {
    "owner": "Noctria",
    "retries": 0,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    dag_id="veritas_recheck_dag",
    start_date=datetime(2025, 7, 1),
    schedule_interval=None,
    catchup=False,
    default_args=default_args,
    tags=["veritas", "recheck"],
) as dag:

    recheck_task = PythonOperator(
        task_id="recheck_strategy",
        python_callable=recheck_strategy,
        provide_context=True,
    )
