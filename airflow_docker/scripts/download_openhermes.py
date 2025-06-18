from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_ID = "openaccess-ai-collective/openhermes-2.5-mistral-7b"
MODEL_DIR = "/opt/airflow/models/openhermes2.5"

def download():
    print(f"🔽 モデルを {MODEL_ID} から {MODEL_DIR} にダウンロード中...")
    model = AutoModelForCausalLM.from_pretrained(MODEL_ID)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model.save_pretrained(MODEL_DIR)
    tokenizer.save_pretrained(MODEL_DIR)
    print("✅ モデルダウンロード完了")

if __name__ == "__main__":
    download()
