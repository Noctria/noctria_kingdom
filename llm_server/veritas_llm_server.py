# veritas_llm_server.py

import os
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# === モデル読み込み（グローバルに一度だけ） ===
MODEL_DIR = os.getenv("MODEL_DIR", "/noctria_kingdom/airflow_docker/models/nous-hermes-2")

if not os.path.exists(MODEL_DIR):
    raise RuntimeError(f"❌ モデルディレクトリが見つかりません: {MODEL_DIR}")

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, local_files_only=True)
model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, local_files_only=True)

# === FastAPI 初期化 ===
app = FastAPI(title="Veritas LLM Server")

class PromptRequest(BaseModel):
    prompt: str
    max_tokens: int = 300

@app.post("/run_veritas_llm")
def generate_response(data: PromptRequest):
    try:
        inputs = tokenizer(data.prompt, return_tensors="pt")
        with torch.no_grad():
            outputs = model.generate(inputs["input_ids"], max_new_tokens=data.max_tokens)
        result = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return {"response": result.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 推論エラー: {str(e)}")

@app.get("/")
def healthcheck():
    return {"status": "🧠 Veritas LLMサーバー起動中"}

# === サーバー起動用エントリーポイント ===
if __name__ == "__main__":
    uvicorn.run("veritas_llm_server:app", host="0.0.0.0", port=8000)
