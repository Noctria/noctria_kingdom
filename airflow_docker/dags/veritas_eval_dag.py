import os
import importlib.util
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

# 評価用シミュレータ関数
from core.strategy_optimizer_adjusted import simulate_strategy_adjusted
from core.market_loader import load_market_data  # 独立しているなら適宜修正

# === DAG設定 ===
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

# === 評価関数 ===
def evaluate_and_adopt_strategies(**kwargs):
    generated_dir = "/noctria_kingdom/strategies/veritas_generated"
    official_dir = "/noctria_kingdom/strategies/official"
    os.makedirs(official_dir, exist_ok=True)

    market_data = load_market_data("market_data.csv")

    for filename in os.listdir(generated_dir):
        if filename.endswith(".py"):
            path = os.path.join(generated_dir, filename)
            spec = importlib.util.spec_from_file_location("candidate", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if not hasattr(module, "simulate"):
                print(f"⚠️ {filename} に simulate() が見つかりません")
                continue

            try:
                final_capital = module.simulate(market_data)
                print(f"📈 評価: {filename} ➜ 資産 {final_capital:,.0f}円")

                if final_capital >= 1050000:
                    save_path = os.path.join(official_dir, filename)
                    with open(path, "r") as src, open(save_path, "w") as dst:
                        dst.write(src.read())
                    print(f"✅ 採用: {filename} を official/ に保存")
                else:
                    print(f"❌ 不採用: {filename}")

            except Exception as e:
                print(f"🚫 評価エラー: {filename} ➜ {e}")

# === DAGタスク定義 ===
with dag:
    evaluate_task = PythonOperator(
        task_id='evaluate_and_adopt_generated_strategies',
        python_callable=evaluate_and_adopt_strategies,
        provide_context=True,
    )
