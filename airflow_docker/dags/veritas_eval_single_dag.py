# airflow_docker/dags/veritas_eval_single_dag.py

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.python import get_current_context

from datetime import datetime, timedelta
import os
import json

from core.path_config import STRATEGIES_DIR, LOGS_DIR, DATA_DIR
from core.market_loader import load_market_data
from core.strategy_evaluator import evaluate_strategy, is_strategy_adopted

default_args = {
    'owner': 'Veritas',
    'depends_on_past': False,
    'start_date': datetime(2025, 6, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=2),
}

dag = DAG(
    dag_id='veritas_eval_single_dag',
    default_args=default_args,
    description='🔍 単体戦略評価 DAG（strategy_name を conf で指定）',
    schedule_interval=None,
    catchup=False,
    tags=['veritas', 'evaluation', 'single', 'pdca'],
)

def evaluate_single_strategy():
    context = get_current_context()
    conf = context.get("dag_run").conf or {}

    strategy_name = conf.get("strategy_name")
    if not strategy_name:
        raise ValueError("strategy_name が指定されていません")

    strategy_path = STRATEGIES_DIR / "veritas_generated" / strategy_name
    if not strategy_path.exists():
        raise FileNotFoundError(f"指定された戦略が見つかりません: {strategy_path}")

    official_dir = STRATEGIES_DIR / "official"
    log_path = LOGS_DIR / "veritas_eval_result.json"
    market_data_path = DATA_DIR / "market_data.csv"

    os.makedirs(official_dir, exist_ok=True)
    os.makedirs(log_path.parent, exist_ok=True)

    market_data = load_market_data(str(market_data_path))
    result = evaluate_strategy(str(strategy_path), market_data)

    if is_strategy_adopted(result):
        save_path = official_dir / strategy_name
        with open(strategy_path, "r") as src, open(save_path, "w") as dst:
            dst.write(src.read())
        print(f"✅ 採用: {strategy_name}（資産 {result['final_capital']:,.0f}円）")
        result["status"] = "adopted"
    elif result["status"] == "ok":
        print(f"❌ 不採用: {strategy_name}")
        result["status"] = "rejected"
    else:
        print(f"🚫 エラー: {strategy_name} ➜ {result.get('error_message')}")

    # ✅ ログ記録
    if log_path.exists():
        with open(log_path, "r") as f:
            logs = json.load(f)
    else:
        logs = []

    logs.append(result)
    with open(log_path, "w") as f:
        json.dump(logs, f, indent=2)

# === DAG登録 ===
with dag:
    evaluate_task = PythonOperator(
        task_id='evaluate_single_strategy',
        python_callable=evaluate_single_strategy,
    )
