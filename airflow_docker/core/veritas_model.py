import os
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# ✅ モデルディレクトリの環境変数取得（またはデフォルト）
MODEL_DIR = os.getenv("MODEL_DIR", "/noctria_kingdom/airflow_docker/models/nous-hermes-2")
print(f"📦 使用モデルディレクトリ: {MODEL_DIR}")

if not os.path.isdir(MODEL_DIR):
    raise FileNotFoundError(f"❌ モデルディレクトリが存在しません: {MODEL_DIR}")

# ✅ GPU確認ログ
if torch.cuda.is_available():
    print(f"🚀 GPU使用可能: {torch.cuda.get_device_name(0)}")
else:
    print("⚠️ GPUが使用できません（CPUで実行されます）")

# ✅ モデル・トークナイザー読み込み（device_map="auto" を使用）
model = AutoModelForCausalLM.from_pretrained(
    MODEL_DIR,
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    device_map="auto",                  # ← ここが重要
    low_cpu_mem_usage=True,
    local_files_only=True
)

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, local_files_only=True)

def generate_fx_strategy(prompt: str) -> str:
    """為替戦略を生成"""
    inputs = tokenizer(prompt, return_tensors="pt")
    if torch.cuda.is_available():
        inputs = {k: v.to("cuda") for k, v in inputs.items()}

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
