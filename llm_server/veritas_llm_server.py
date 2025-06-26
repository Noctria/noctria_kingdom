from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import os

app = FastAPI()

# モデルのローカルディレクトリ
MODEL_PATH = "/home/user/noctria_kingdom/airflow_docker/models/openchat-3.5"
print(f"📦 モデル読み込み中: {MODEL_PATH}")

# 明示的に config, tokenizer, model の全パスを指定（完全ローカル）
tokenizer = AutoTokenizer.from_pretrained(
    os.path.abspath(MODEL_PATH),
    local_files_only=True
)

model = AutoModelForCausalLM.from_pretrained(
    os.path.abspath(MODEL_PATH),
    local_files_only=True
)
model.eval()

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

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
    result = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return {"response": result}
