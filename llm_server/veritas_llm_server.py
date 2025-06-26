from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# ✅ モデルのローカルパスを指定
MODEL_DIR = "/home/noctria/noctria-kingdom-main/airflow_docker/models/openchat-3.5"

print(f"📦 モデル読み込み中: {MODEL_DIR}")

# ✅ ローカルファイルのみを使って読み込むよう指定
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_DIR,
    trust_remote_code=True,
    local_files_only=True
)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_DIR,
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    trust_remote_code=True,
    local_files_only=True
)

model.eval()
device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)

# ✅ FastAPI アプリケーション定義
app = FastAPI(title="Veritas LLM Server (OpenChat 3.5)")

# ✅ リクエスト用スキーマ
class PromptRequest(BaseModel):
    prompt: str
    max_tokens: int = 300

# ✅ 推論エンドポイント
@app.post("/predict")
def predict(request: PromptRequest):
    inputs = tokenizer(request.prompt, return_tensors="pt").to(device)
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=request.max_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.9
        )
    response = tokenizer.decode(output[0], skip_special_tokens=True)
    return {"response": response}
