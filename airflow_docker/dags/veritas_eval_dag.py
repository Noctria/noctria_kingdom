import os
import json
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

# 評価関数の依存モジュール（← module動的importを外部関数に移譲）
from core.strategy_optimizer_adjusted import simulate_strategy_adjusted
from core.market_loader import load_market_data  # 必要に応じて修正

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
    description='✅ Veritas生成戦略の評価・採用判定DAG',
    schedule_interval=None,
    catchup=False,
    tags=['veritas', 'evaluation', 'pdca'],
)

def evaluate_and_adopt_strategies(**kwargs):
    generated_dir = "/noctria_kingdom/strategies/veritas_generated"
    official_dir = "/noctria_kingdom/strategies/official"
    log_path = "/noctria_kingdom/airflow_docker/logs/veritas_eval_result.json"

    os.makedirs(official_dir, exist_ok=True)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    # ✅ 市場データの読み込み
    market_data = load_market_data("market_data.csv")

    # ✅ ログ読み込み or 初期化
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            eval_logs = json.load(f)
    else:
        eval_logs = []

    for filename in os.listdir(generated_dir):
        if not filename.endswith(".py"):
            continue

        path = os.path.join(generated_dir, filename)

        try:
            # ✅ 評価を共通関数で実行
            final_capital = simulate_strategy_adjusted(path, market_data)
            print(f"📈 評価: {filename} ➜ 資産 {final_capital:,.0f}円")

            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "filename": filename,
                "final_capital": final_capital,
                "status": "adopted" if final_capital >= 1050000 else "rejected"
            }

            if final_capital >= 1050000:
                save_path = os.path.join(official_dir, filename)
                with open(path, "r") as src, open(save_path, "w") as dst:
                    dst.write(src.read())
                print(f"✅ 採用: {filename} を official/ に保存")
            else:
                print(f"❌ 不採用: {filename}")

            eval_logs.append(log_entry)

        except Exception as e:
            print(f"🚫 評価エラー: {filename} ➜ {e}")
            eval_logs.append({
                "timestamp": datetime.utcnow().isoformat(),
                "filename": filename,
                "final_capital": None,
                "status": f"error: {str(e)}"
            })

    # ✅ ログ保存
    with open(log_path, "w") as f:
        json.dump(eval_logs, f, indent=2)

with dag:
    evaluate_task = PythonOperator(
        task_id='evaluate_and_adopt_generated_strategies',
        python_callable=evaluate_and_adopt_strategies,
        provide_context=True,
    )
