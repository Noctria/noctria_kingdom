import os
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# ✅ モデルディレクトリの環境変数取得（またはデフォルト）
MODEL_DIR = os.getenv("MODEL_DIR", "/noctria_kingdom/airflow_docker/models/nous-hermes-2")

print(f"📦 使用モデルディレクトリ: {MODEL_DIR}")

if not os.path.isdir(MODEL_DIR):
    raise FileNotFoundError(f"❌ モデルディレクトリが存在しません: {MODEL_DIR}")

# ✅ ローカルファイル限定で読み込み（Hugging Face Hubへのアクセスを防止）
model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, local_files_only=True)
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, local_files_only=True)

def generate_fx_strategy(prompt: str) -> str:
    """為替戦略を生成"""
    inputs = tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        outputs = model.generate(inputs["input_ids"], max_new_tokens=300)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)
