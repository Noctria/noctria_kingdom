from transformers import AutoModelForCausalLM, AutoTokenizer
import os

# モデルIDと保存先ディレクトリ
MODEL_ID = "openaccess-ai-collective/openhermes-2.5-mistral-7b"
MODEL_DIR = "/noctria_kingdom/airflow_docker/models/openhermes2.5"

# Hugging Face トークン（.env で渡す）
HF_TOKEN = os.getenv("HF_TOKEN")

def download():
    if not HF_TOKEN:
        raise ValueError("❌ HF_TOKEN が未設定です。`.env` に追加し、docker-compose.yaml で渡してください。")

    print(f"🔽 モデルを {MODEL_ID} から {MODEL_DIR} にダウンロード中...")

    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, use_auth_token=HF_TOKEN)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, use_auth_token=HF_TOKEN)

    os.makedirs(MODEL_DIR, exist_ok=True)
    model.save_pretrained(MODEL_DIR)
    tokenizer.save_pretrained(MODEL_DIR)

    print("✅ モデルダウンロード完了")

if __name__ == "__main__":
    download()
