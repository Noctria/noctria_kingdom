import os
import torch
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM
from dotenv import load_dotenv

# ✅ .env 読み込み（MODEL_DIR=/home/user/noctria-kingdom-main/airflow_docker/models/openchat-3.5-0106 など）
load_dotenv()
model_path = os.getenv("MODEL_DIR", "/home/user/noctria-kingdom-main/airflow_docker/models/openchat-3.5-0106")

# ✅ モデル存在チェック
if not os.path.exists(model_path):
    raise RuntimeError(f"❌ モデルディレクトリが見つかりません: {model_path}")

print(f"📦 モデル読み込み中: {model_path}")
torch.cuda.empty_cache()

# ✅ モデルとトークナイザーの読み込み（OpenChatは trust_remote_code 必須）
tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    torch_dtype=torch.float16,
    device_map="auto",
    trust_remote_code=True
)
model.eval()

# ✅ FastAPI サーバー
app = FastAPI()

class PromptRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 128
    temperature: float = 0.7

@app.get("/")
def root():
    return {"message": "🧠 Veritas LLMサーバー稼働中（OpenChat）"}

@app.post("/generate")
def generate(req: PromptRequest):
    inputs = tokenizer(req.prompt, return_tensors="pt").to(model.device)
    outputs = model.generate(
        **inputs,
        max_new_tokens=req.max_new_tokens,
        temperature=req.temperature,
        do_sample=True,
        top_p=0.95,
    )
    result = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return {"response": result}
