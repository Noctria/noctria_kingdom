from core.path_config import CORE_DIR, DAGS_DIR, DATA_DIR, INSTITUTIONS_DIR, LOGS_DIR, MODELS_DIR, PLUGINS_DIR, SCRIPTS_DIR, STRATEGIES_DIR, TESTS_DIR, TOOLS_DIR, VERITAS_DIR
import os
import json
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

# ✅ Noctria Kingdom v2.0 パス一元管理
from core.path_config import (
    STRATEGIES_DIR,
    LOGS_DIR,
    DATA_DIR
)

from core.strategy_optimizer_adjusted import simulate_strategy_adjusted
from core.market_loader import load_market_data

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
    description='✅ Veritas生成戦略の評価・採用判定DAG（dict対応）',
    schedule_interval=None,
    catchup=False,
    tags=['veritas', 'evaluation', 'pdca'],
)

# === 評価＆昇格処理 ===
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
        print(f"🔍 評価対象: {filename}")

        result = simulate_strategy_adjusted(str(path), market_data)

        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "filename": filename,
            "status": result.get("status", "error"),
            "final_capital": result.get("final_capital"),
            "win_rate": result.get("win_rate"),
            "max_drawdown": result.get("max_drawdown"),
            "total_trades": result.get("total_trades"),
            "error_message": result.get("error_message")
        }

        if result["status"] == "ok" and result.get("final_capital", 0) >= 1_050_000:
            save_path = official_dir / filename
            with open(path, "r") as src, open(save_path, "w") as dst:
                dst.write(src.read())
            print(f"✅ 採用: {filename}（資産 {result['final_capital']:,.0f}円）")
            log_entry["status"] = "adopted"
        elif result["status"] == "ok":
            print(f"❌ 不採用: {filename}（資産 {result['final_capital']:,.0f}円）")
            log_entry["status"] = "rejected"
        else:
            print(f"🚫 エラー: {filename} ➜ {result['error_message']}")

        eval_logs.append(log_entry)

    with open(log_path, "w") as f:
        json.dump(eval_logs, f, indent=2)

# === DAGへ登録 ===
with dag:
    evaluate_task = PythonOperator(
        task_id='evaluate_and_adopt_generated_strategies',
        python_callable=evaluate_and_adopt_strategies,
    )