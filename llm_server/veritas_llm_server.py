# llm_server/veritas_llm_server.py

import os
import torch
import time
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM
from dotenv import load_dotenv

from veritas.generate.llm_prompt_builder import load_strategy_template

# ✅ .env読み込み
load_dotenv()
model_path = os.getenv("MODEL_DIR", "/home/user/noctria-kingdom-main/airflow_docker/models/elyza-7b-instruct")

# ✅ モデル存在チェック
if not os.path.exists(model_path):
    raise RuntimeError(f"❌ モデルディレクトリが見つかりません: {model_path}")

print(f"📦 モデル読み込み中: {model_path}")
torch.cuda.empty_cache()

# ✅ モデル・トークナイザーの読み込み
tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    device_map="auto",
    trust_remote_code=True
)
model.eval()

# ✅ FastAPI サーバー初期化
app = FastAPI()
strategy_template = load_strategy_template()

# ✅ リクエスト形式
class PromptRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 128
    temperature: float = 0.7
    top_p: float = 0.95
    do_sample: bool = True

@app.get("/")
def root():
    return {"message": "🧠 Veritas LLMサーバー稼働中（テンプレ統合済み）"}

@app.post("/generate")
def generate(req: PromptRequest):
    start_time = time.time()

    # ✅ テンプレート組込み
    full_prompt = f"""あなたはAI戦略生成者Veritasです。
以下のテンプレートに準拠した形式で、新しい戦略をPythonコードで生成してください。

--- 戦略テンプレート ---
{strategy_template}

--- ユーザー指示 ---
{req.prompt}
"""

    # ✅ Tokenize & Generate
    inputs = tokenizer(
        full_prompt,
        return_tensors="pt",
        truncation=True,  # 長過ぎる入力をカット
        max_length=2048   # モデルの制限に応じて調整
    ).to(model.device)

    outputs = model.generate(
        **inputs,
        max_new_tokens=req.max_new_tokens,
        temperature=req.temperature,
        top_p=req.top_p,
        do_sample=req.do_sample
    )

    result = tokenizer.decode(outputs[0], skip_special_tokens=True)

    elapsed = round(time.time() - start_time, 2)
    print(f"🕒 推論時間: {elapsed}s | 📝 入力長: {len(full_prompt)}文字")

    return {
        "response": result,
        "elapsed_time": elapsed,
        "input_length": len(full_prompt)
    }
