from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from pathlib import Path

# 明示的に Path オブジェクトとして定義
MODEL_DIR = Path("/home/noctria/noctria-kingdom-main/airflow_docker/models/openchat-3.5").resolve()

print(f"📦 モデル読み込み中: {MODEL_DIR}")

# ローカルファイルのみでロード
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

app = FastAPI()

class PromptRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 128

@app.post("/generate")
def generate_text(req: PromptRequest):
    inputs = tokenizer(req.prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=req.max_new_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.95
        )
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return {"response": response}
