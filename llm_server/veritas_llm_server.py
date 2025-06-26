# llm_server/veritas_llm_server.py

from fastapi import FastAPI, Request
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

app = FastAPI()

# モデルパス（ローカル）
MODEL_DIR = "/home/user/noctria_kingdom/airflow_docker/models/openchat-3.5"
print(f"📦 モデル読み込み中: {MODEL_DIR}")

# ローカルからトークナイザーとモデルを読み込む
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_DIR,
    local_files_only=True,
    use_auth_token=None
)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_DIR,
    local_files_only=True,
    use_auth_token=None
)
model.eval()

# CUDAが利用可能なら使用
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# リクエスト用モデル
class PromptRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 100
    temperature: float = 0.7

@app.post("/generate")
async def generate_text(request: PromptRequest):
    inputs = tokenizer(request.prompt, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=request.max_new_tokens,
            temperature=request.temperature,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return {"response": response}
