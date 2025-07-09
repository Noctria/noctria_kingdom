from core.path_config import STRATEGIES_DIR, LOGS_DIR, DATA_DIR
from core.strategy_evaluator import evaluate_strategy, is_strategy_adopted
from core.market_loader import load_market_data

import os
import json
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

# === DAG基本設定 ===
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
    dag_id='veritas_eval_dag',
    default_args=default_args,
    description='✅ Veritas生成戦略の評価・採用判定DAG（共通評価関数対応）',
    schedule_interval=None,
    catchup=False,
    tags=['veritas', 'evaluation', 'pdca'],
)

def evaluate_and_adopt_strategies():
    generated_dir = STRATEGIES_DIR / "veritas_generated"
    official_dir = STRATEGIES_DIR / "official"
    log_path = LOGS_DIR / "veritas_eval_result.json"
    data_csv_path = DATA_DIR / "market_data.csv"

    os.makedirs(official_dir, exist_ok=True)
    os.makedirs(log_path.parent, exist_ok=True)

    market_data = load_market_data(str(data_csv_path))

    if log_path.exists():
        with open(log_path, "r") as f:
            eval_logs = json.load(f)
    else:
        eval_logs = []

    for filename in os.listdir(generated_dir):
        if not filename.endswith(".py"):
            continue

        path = generated_dir / filename
        print(f"📊 評価中: {filename}")
        result = evaluate_strategy(str(path), market_data)

        if is_strategy_adopted(result):
            save_path = official_dir / filename
            with open(path, "r") as src, open(save_path, "w") as dst:
                dst.write(src.read())
            print(f"✅ 採用: {filename}（資産 {result['final_capital']:,.0f}円）")
            result["status"] = "adopted"
        elif result["status"] == "ok":
            print(f"❌ 不採用: {filename}")
            result["status"] = "rejected"
        else:
            print(f"🚫 エラー: {filename} ➜ {result.get('error_message')}")

        eval_logs.append(result)

    with open(log_path, "w") as f:
        json.dump(eval_logs, f, indent=2)

# === DAGへ登録 ===
with dag:
    evaluate_task = PythonOperator(
        task_id='evaluate_and_adopt_generated_strategies',
        python_callable=evaluate_and_adopt_strategies,
    )
