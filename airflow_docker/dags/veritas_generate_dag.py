import os
import logging
import psycopg2
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# 環境変数取得
DB_NAME = os.getenv("POSTGRES_DB", "airflow")
DB_USER = os.getenv("POSTGRES_USER", "airflow")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "airflow")
DB_HOST = os.getenv("POSTGRES_HOST", "postgres")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

MODEL_DIR = os.getenv("MODEL_DIR", "/noctria_kingdom/airflow_docker/models/nous-hermes-2")

# モデルとトークナイザーをキャッシュ用グローバル変数に格納（初期はNone）
model = None
tokenizer = None

def load_model():
    global model, tokenizer
    if model is None or tokenizer is None:
        if not os.path.exists(MODEL_DIR):
            raise FileNotFoundError(f"❌ モデルディレクトリが存在しません: {MODEL_DIR}")
        model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, local_files_only=True)
        tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, local_files_only=True)

def generate_fx_strategy(prompt: str) -> str:
    load_model()
    inputs = tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        outputs = model.generate(inputs["input_ids"], max_new_tokens=300)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

def run_veritas_and_save():
    prompt = "USDJPYについて、来週のFX戦略を日本語で5つ提案してください。"
    response = generate_fx_strategy(prompt)

    conn = None
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO veritas_outputs (prompt, response)
                VALUES (%s, %s)
                """,
                (prompt, response)
            )
            conn.commit()
        print("✅ 戦略出力をDBに保存しました。")

    except Exception as e:
        logging.error("🚨 DB保存に失敗: %s", e)
        raise

    finally:
        if conn:
            conn.close()

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
