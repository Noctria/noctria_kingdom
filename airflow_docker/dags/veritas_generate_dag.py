import os
import logging
import sys
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

# 🔁 モデル呼び出し関数
from core.veritas_llm import generate_fx_strategy

# 📜 ログ設定
logger = logging.getLogger("veritas_dag")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)

# 📌 DAG定義
with DAG(
    dag_id="veritas_generate_dag",
    start_date=datetime(2025, 6, 1),
    schedule_interval=None,  # マニュアル実行（または必要に応じて定期化）
    catchup=False,
    tags=["veritas", "llm", "strategy"]
) as dag:

    def generate_and_log():
        prompt = os.getenv("VERITAS_PROMPT", "次のUSDJPY戦略を5つ考えてください。")
        logger.info(f"📤 プロンプト送信: {prompt}")
        
        result = generate_fx_strategy(prompt)
        logger.info("✅ 応答:")
        logger.info(result)

        # ✍️ 生成結果をファイルにも保存（任意）
        output_path = "/noctria_kingdom/airflow_docker/logs/veritas_output.txt"
        with open(output_path, "a", encoding="utf-8") as f:
            f.write(f"\n\n=== {datetime.now()} ===\n")
            f.write(result)

    generate_fx_strategy_task = PythonOperator(
        task_id="generate_fx_strategy",
        python_callable=generate_and_log
    )
