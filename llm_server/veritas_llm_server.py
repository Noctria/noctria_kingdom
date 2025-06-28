import os
import torch
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM
from dotenv import load_dotenv

# ✅ .env 読み込み
load_dotenv()
model_path = os.getenv("MODEL_DIR", "/home/user/noctria-kingdom-main/airflow_docker/models/elyza-7b-instruct")

# ✅ モデル存在チェック
if not os.path.exists(model_path):
    raise RuntimeError(f"❌ モデルディレクトリが見つかりません: {model_path}")

print(f"📦 モデル読み込み中: {model_path}")
torch.cuda.empty_cache()

# ✅ モデルとトークナイザーの読み込み
tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    device_map="auto",
    trust_remote_code=True
)
model.eval()

# ✅ FastAPI サーバー
app = FastAPI()

# ✅ リクエスト定義（top_p, do_sampleを含めて柔軟化）
class PromptRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 128
    temperature: float = 0.7
    top_p: float = 0.95
    do_sample: bool = True

@app.get("/")
def root():
    return {"message": "🧠 Veritas LLMサーバー稼働中（OpenChat）"}

@app.post("/generate")
def generate(req: PromptRequest):
    # ✅ 入力をモデルのデバイスに転送
    inputs = tokenizer(req.prompt, return_tensors="pt").to(model.device)

    # ✅ 生成実行（すべてのパラメータを反映）
    outputs = model.generate(
        **inputs,
        max_new_tokens=req.max_new_tokens,
        temperature=req.temperature,
        top_p=req.top_p,
        do_sample=req.do_sample
    )

    result = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return {"response": result}
