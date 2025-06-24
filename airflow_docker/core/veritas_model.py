import os
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# ✅ モデルディレクトリの環境変数取得（またはデフォルト）
MODEL_DIR = os.getenv("MODEL_DIR", "/noctria_kingdom/airflow_docker/models/nous-hermes-2")
print(f"📦 使用モデルディレクトリ: {MODEL_DIR}")

if not os.path.isdir(MODEL_DIR):
    raise FileNotFoundError(f"❌ モデルディレクトリが存在しません: {MODEL_DIR}")

# ✅ 実行デバイスを自動判定（CPU / CUDA）
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ✅ モデル・トークナイザー読み込み（低メモリ設定＋ローカルのみ）
model = AutoModelForCausalLM.from_pretrained(
    MODEL_DIR,
    torch_dtype=torch.float16 if device.type == "cuda" else torch.float32,
    low_cpu_mem_usage=True,
    local_files_only=True
).to(device)

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, local_files_only=True)

def generate_fx_strategy(prompt: str) -> str:
    """為替戦略を生成"""
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model.generate(
            inputs["input_ids"],
            max_new_tokens=300,
            temperature=0.7,
            top_p=0.95,
            do_sample=True
        )
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

# ✅ テスト実行用
if __name__ == "__main__":
    prompt = (
        "あなたは為替市場の戦略AIです。\n"
        "現在のドル円相場は高ボラティリティかつ方向感がありません。\n"
        "短期スキャルピングに有効な戦略を、具体的なルールとして提示してください。\n"
    )
    result = generate_fx_strategy(prompt)
    print("=== Veritasの提案 ===\n", result)
