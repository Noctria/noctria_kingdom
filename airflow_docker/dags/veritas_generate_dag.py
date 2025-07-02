import os
import logging
import psycopg2
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from transformers import AutoModelForCausalLM, AutoTokenizer
from dotenv import load_dotenv
import torch

# ✅ パス集中管理（v2.0対応）
from core.path_config import MODELS_DIR, STRATEGIES_DIR, CORE_DIR

# ✅ .env 読み込み（Airflow起動時に一度だけ読み込まれる想定）
load_dotenv(dotenv_path=str(CORE_DIR.parent / ".env"))

# === 環境変数 ===
DB_NAME = os.getenv("POSTGRES_DB", "airflow")
DB_USER = os.getenv("POSTGRES_USER", "airflow")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "airflow")
DB_HOST = os.getenv("POSTGRES_HOST", "postgres")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
MODEL_DIR = os.getenv("MODEL_DIR", str(MODELS_DIR / "nous-hermes-2"))

GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# === モデルロードキャッシュ ===
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

def save_and_push_strategy(code: str, strategy_name: str = None):
    from subprocess import run
    now = datetime.now().strftime("%Y%m%d_%H%M")
    filename = strategy_name or f"strategy_{now}.py"
    save_dir = STRATEGIES_DIR / "veritas_generated"
    save_path = save_dir / filename

    os.makedirs(save_dir, exist_ok=True)
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(code)

    print(f"💾 戦略を保存しました: {save_path}")

    try:
        run(["git", "add", str(save_path)], check=True)
        run(["git", "commit", "-m", f"🤖 Veritas戦略自動追加: {filename}"], check=True)
        if GITHUB_TOKEN:
            remote = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_USERNAME}/{GITHUB_REPO}.git"
            run(["git", "push", remote], check=True)
        else:
            run(["git", "push"], check=True)
        print("🚀 GitHubにPush完了")
    except Exception as e:
        logging.error("❌ GitHub Push失敗: %s", e)
        raise

def run_veritas_and_save():
    prompt = "USDJPYについて、来週のFX戦略を日本語で5つ提案してください。"
    response = generate_fx_strategy(prompt)

    # ✅ PostgreSQL保存
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
        print("✅ 戦略をDBに保存しました。")
    except Exception as e:
        logging.error("🚨 DB保存に失敗: %s", e)
        raise
    finally:
        if conn:
            conn.close()

    # ✅ GitHubへ戦略反映
    save_and_push_strategy(response)

# === DAG定義 ===
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
