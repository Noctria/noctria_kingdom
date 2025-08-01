#!/usr/bin/env python3
# coding: utf-8

"""
🦉 Hermes Cognitor LLM戦略コード生成スクリプト
- LLM（GPT, Claude, local transformers等）で自然言語プロンプト→Python戦略コードを生成
- Hermes大臣はナラティブ・説明・自然言語アルゴリズム化を担当
"""

import os
import torch
import psycopg2
from datetime import datetime
from transformers import AutoModelForCausalLM, AutoTokenizer
import re

from src.core.path_config import MODELS_DIR, STRATEGIES_DIR, LOGS_DIR
from src.core.logger import setup_logger

logger = setup_logger("HermesGenerator", LOGS_DIR / "hermes" / "generator.log")

# --- 環境変数
DB_NAME = os.getenv("POSTGRES_DB", "airflow")
DB_USER = os.getenv("POSTGRES_USER", "airflow")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "airflow")
DB_HOST = os.getenv("POSTGRES_HOST", "postgres")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
MODEL_PATH = os.getenv("MODEL_DIR", str(MODELS_DIR / "nous-hermes-2"))

# --- LLMモデルのロード ---
def load_llm_model():
    if not os.path.exists(MODEL_PATH):
        logger.error(f"❌ モデルディレクトリが存在しません: {MODEL_PATH}")
        raise FileNotFoundError(f"Model directory not found: {MODEL_PATH}")
    logger.info(f"🧠 LLMモデルをロード中: {MODEL_PATH}")
    model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, local_files_only=True)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)
    logger.info("✅ LLMモデルのロード完了")
    return model, tokenizer

# --- プロンプト生成（Hermes仕様：自然言語→戦略コード）---
def build_prompt(symbol: str, tag: str, target_metric: str) -> str:
    prompt = (
        f"あなたはプロの金融エンジニアです。通貨ペア'{symbol}'を対象とし、"
        f"'{tag}'という特性を持つ取引戦略をPythonで記述してください。"
        f"この戦略は特に'{target_metric}'という指標を最大化することを目的とします。"
        "コードには、戦略のロジックを実装した`simulate()`関数を含めてください。"
    )
    logger.info(f"📝 生成されたプロンプト: {prompt[:100]}...")
    return prompt

# --- 戦略生成 ---
def generate_strategy_code(prompt: str) -> str:
    model, tokenizer = load_llm_model()
    inputs = tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        outputs = model.generate(inputs["input_ids"], max_new_tokens=1024, pad_token_id=tokenizer.eos_token_id)
    generated_code = tokenizer.decode(outputs[0], skip_special_tokens=True)

    # 安全にPythonコード部分を抽出（def simulate以降）
    match = re.search(r"(def simulate\(.*)", generated_code, re.DOTALL)
    code_only = match.group(1).strip() if match else generated_code.strip()

    logger.info("🤖 Hermesによる戦略コードの生成完了")
    return code_only

# --- DB保存（生成プロンプト/コード記録）---
def save_to_db(prompt: str, response: str):
    conn = None
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
        )
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO hermes_outputs (prompt, response, created_at) VALUES (%s, %s, %s)",
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
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"hermes_{tag}_{now}.py"
    save_dir = STRATEGIES_DIR / "hermes_generated"
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / filename
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(code)
    logger.info(f"💾 戦略をファイルに保存しました: {save_path}")
    return str(save_path)

# --- サンプル実行ブロック ---
if __name__ == "__main__":
    symbol = "USDJPY"
    tag = "trend_breakout"
    target_metric = "win_rate"
    prompt = build_prompt(symbol, tag, target_metric)
    code = generate_strategy_code(prompt)
    save_to_file(code, tag)
    save_to_db(prompt, code)
    print("🦉 Hermes大臣による自動戦略生成デモ完了！")
