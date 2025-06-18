import os
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

MODEL_DIR = os.getenv("MODEL_DIR", "/noctria_kingdom/airflow_docker/models/nous-hermes-2")

if not os.path.exists(MODEL_DIR):
    raise FileNotFoundError(f"❌ モデルディレクトリが存在しません: {MODEL_DIR}")

# ✅ ローカルフォルダ指定を明示的に
model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, local_files_only=True)
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, local_files_only=True)

def generate_fx_strategy(prompt: str) -> str:
    inputs = tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        outputs = model.generate(inputs["input_ids"], max_new_tokens=300)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)
