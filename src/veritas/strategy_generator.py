# src/veritas/strategy_generator.py

import os
import torch
import psycopg2
from datetime import datetime
from transformers import AutoModelForCausalLM, AutoTokenizer

# --- 王国の中枢モジュールをインポート ---
# ★ 修正点: LOGS_DIRをインポートリストに追加
from core.path_config import MODELS_DIR, STRATEGIES_DIR, LOGS_DIR
from core.logger import setup_logger

# --- 専門家の記録係をセットアップ ---
logger = setup_logger("VeritasGenerator", LOGS_DIR / "veritas" / "generator.log")

# --- 環境変数 (core.settings に集約するのが望ましい) ---
DB_NAME = os.getenv("POSTGRES_DB", "airflow")
DB_USER = os.getenv("POSTGRES_USER", "airflow")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "airflow")
DB_HOST = os.getenv("POSTGRES_HOST", "postgres")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
MODEL_PATH = os.getenv("MODEL_DIR", str(MODELS_DIR / "nous-hermes-2"))

# --- LLMモデルのロード ---
def load_llm_model():
    """LLMモデルとトークナイザーをロードする"""
    if not os.path.exists(MODEL_PATH):
        logger.error(f"❌ モデルディレクトリが存在しません: {MODEL_PATH}")
        raise FileNotFoundError(f"Model directory not found: {MODEL_PATH}")
    
    logger.info(f"🧠 LLMモデルをロード中: {MODEL_PATH}")
    model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, local_files_only=True)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)
    logger.info("✅ LLMモデルのロード完了")
    return model, tokenizer

# --- プロンプト生成 ---
def build_prompt(symbol: str, tag: str, target_metric: str) -> str:
    """DAGのコンフィグからプロンプトを生成する"""
    prompt = f"あなたはプロの金融エンジニアです。通貨ペア'{symbol}'を対象とし、'{tag}'という特性を持つ取引戦略をPythonで記述してください。この戦略は特に'{target_metric}'という指標を最大化することを目的とします。コードには、戦略のロジックを実装した`simulate()`関数を含めてください。"
    logger.info(f"📝 生成されたプロンプト: {prompt[:100]}...")
    return prompt

# --- 戦略生成 ---
def generate_strategy_code(prompt: str) -> str:
    """プロンプトを元にLLMで戦略コードを生成する"""
    model, tokenizer = load_llm_model()
    inputs = tokenizer(prompt, return_tensors="pt")
    
    with torch.no_grad():
        outputs = model.generate(inputs["input_ids"], max_new_tokens=1024, pad_token_id=tokenizer.eos_token_id)
        
    generated_code = tokenizer.decode(outputs[0], skip_special_tokens=True)
    # プロンプト部分を除去してコードだけを返す
    code_only = generated_code[len(prompt):].strip()
    logger.info("🤖 LLMによる戦略コードの生成完了")
    return code_only

# --- DB保存 ---
def save_to_db(prompt: str, response: str):
    """生成結果をPostgreSQLに保存する"""
    conn = None
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
        )
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO veritas_outputs (prompt, response, created_at) VALUES (%s, %s, %s)",
                (prompt, response, datetime.now())
            )
            conn.commit()
        logger.info("✅ 生成結果をDBに保存しました。")
    except Exception as e:
        logger.error(f"🚨 DB保存に失敗: {e}", exc_info=True)
        raise
    finally:
        if conn:
            conn.close()

# --- ファイル保存 ---
def save_to_file(code: str, tag: str) -> str:
    """生成されたコードをファイルに保存し、ファイルパスを返す"""
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"veritas_{tag}_{now}.py"
    save_dir = STRATEGIES_DIR / "veritas_generated"
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / filename

    with open(save_path, "w", encoding="utf-8") as f:
        f.write(code)
        
    logger.info(f"💾 戦略をファイルに保存しました: {save_path}")
    return str(save_path)
