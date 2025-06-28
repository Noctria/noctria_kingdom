import os
import torch  # ✅ transformersより前に記述
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM
from dotenv import load_dotenv

# .env 読み込み
load_dotenv()
model_path = os.getenv("MODEL_DIR", "/home/user/noctria-kingdom-main/models/elyza-7b-instruct")

# モデル存在チェック
if not os.path.exists(model_path):
    raise RuntimeError(f"❌ モデルディレクトリが見つかりません: {model_path}")

# モデル・トークナイザー読み込み
print(f"📦 モデル読み込み中: {model_path}")
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
)
model.eval()
model.to("cuda" if torch.cuda.is_available() else "cpu")

# FastAPI アプリ定義
app = FastAPI()

# 入力スキーマ
class PromptRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 128
    temperature: float = 0.7

# 簡易確認用 GET
@app.get("/")
def root():
    return {"message": "🔮 Veritas LLM サーバー稼働中（ELYZAモデル）"}

# 推論エンドポイント
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
