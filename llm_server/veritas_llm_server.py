from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import os

# ✅ モデルのローカルディレクトリ
MODEL_DIR = "/home/user/noctria_kingdom/airflow_docker/models/openchat-3.5"

print(f"📦 モデル読み込み中: {MODEL_DIR}")
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_DIR,
    trust_remote_code=True,
    local_files_only=True,  # ここを追加
    token=None
)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_DIR,
    torch_dtype=torch.float16,
    local_files_only=True,  # ここも追加
    token=None
)
model.eval()

device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)

app = FastAPI(title="Veritas LLM Server (OpenChat 3.5)")

class PromptRequest(BaseModel):
    prompt: str
    max_tokens: int = 300

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
