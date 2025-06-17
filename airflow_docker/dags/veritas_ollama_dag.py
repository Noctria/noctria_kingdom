import os
import requests
import logging
import json
import sys
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime

# 📜 ログ設定
logger = logging.getLogger("veritas_ollama")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)

# 🛠️ DAGの定義
with DAG(
    dag_id="veritas_ollama_dag",  # ✅ DAG ID 明示
    start_date=datetime(2025, 6, 1),
    schedule_interval=None,
    catchup=False,
    tags=["veritas", "ollama"]
) as dag:

    def call_ollama():
        try:
            # 🔧 環境変数から設定を取得
            ollama_host = os.getenv("OLLAMA_HOST", "localhost")
            ollama_port = os.getenv("OLLAMA_PORT", "11434")
            ollama_model = os.getenv("OLLAMA_MODEL", "openhermes")
            ollama_prompt = os.getenv("OLLAMA_PROMPT", "次のUSDJPY戦略を5つ考えてください。")

            # 🌐 API URLを組み立て
            url = f"http://{ollama_host}:{ollama_port}/api/generate"
            logger.info(f"▶️ リクエスト送信先: {url}")

            # 📦 リクエスト送信
            payload = {
                "model": ollama_model,
                "prompt": ollama_prompt
                "stream": False  # ← 明示的にstreamを切る
            }

            response = requests.post(url, json=payload, timeout=20)
            response.raise_for_status()

            # ✅ 結果出力
            result = response.json()
            logger.info("✅ Ollama応答:\n" + json.dumps(result, ensure_ascii=False, indent=2))

        except requests.exceptions.RequestException as e:
            logger.error("🚨 リクエスト失敗:", exc_info=True)
            raise e
        except Exception as e:
            logger.error("🚨 予期せぬエラー:", exc_info=True)
            raise e

    # 📌 PythonOperatorとして登録
    veritas_ollama_prompt = PythonOperator(
        task_id="veritas_ollama_prompt",
        python_callable=call_ollama
    )
