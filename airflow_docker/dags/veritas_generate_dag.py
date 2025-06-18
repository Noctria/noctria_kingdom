import os
import sys
import logging
import psycopg2
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# 🔧 モデルの事前ロード（DAG起動時に一度だけ）
MODEL_DIR = "/noctria_kingdom/airflow_docker/models/nous-hermes-2"
model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, local_files_only=True)
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, local_files_only=True)

# 🧠 戦略生成関数
def generate_fx_strategy(prompt: str) -> str:
    inputs = tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        outputs = model.generate(inputs["input_ids"], max_new_tokens=300)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

# 📥 DB保存付きタスク
def run_veritas_and_save():
    prompt = "USDJPYについて、来週のFX戦略を日本語で5つ提案してください。"
    response = generate_fx_strategy(prompt)

    conn = None
    try:
        # ✅ DB接続（Airflowコンテナ内の接続情報）
        conn = psycopg2.connect(
            dbname="airflow",
            user="airflow",
            password="airflow",
            host="postgres",
            port=5432
        )
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO veritas_outputs (prompt, response)
            VALUES (%s, %s)
            """,
            (prompt, response)
        )
        conn.commit()
        cur.close()
        print("✅ 戦略出力をDBに保存しました。")

    except Exception as e:
        print("🚨 DB保存に失敗:", e)
        raise e

    finally:
        if conn:
            conn.close()

# 🛠️ DAG定義
default_args = {
    'owner': 'Noctria',
    'start_date': datetime(2025, 6, 1),
    'retries': 0,
}

with DAG(
    dag_id='veritas_generate_dag',
    default_args=default_args,
    schedule_interval=None,
    catchup=False,
    tags=["veritas", "llm"]
) as dag:

    generate_and_save_task = PythonOperator(
        task_id="generate_and_save_fx_strategy",
        python_callable=run_veritas_and_save
    )
