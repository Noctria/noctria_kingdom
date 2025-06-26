import os
from fastapi import FastAPI, Request
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# モデルパス（ローカル保存先）
model_path = "/mnt/e/noctria-kingdom-main/airflow_docker/models/openchat-3.5"

# モデルとトークナイザーの読み込み
if not os.path.exists(model_path):
    raise ValueError(f"❌ 指定されたモデルパスが存在しません: {model_path}")

print(f"📦 モデル読み込み中: {model_path}")
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForCausalLM.from_pretrained(model_path, torch_dtype=torch.float16)
model.eval()

# FastAPI アプリ定義
app = FastAPI()

# リクエストの入力形式定義
class PromptRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 128
    temperature: float = 0.7

# 起動確認用
@app.get("/")
def read_root():
    return {"message": "🔮 Veritas LLM サーバー稼働中（OpenChat 3.5）"}

# 推論エンドポイント
@app.post("/generate")
def generate_text(req: PromptRequest):
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
