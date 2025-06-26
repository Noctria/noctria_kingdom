from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from pathlib import Path

app = FastAPI()

# 📦 モデルのパス（必要に応じて変更）
model_path = Path("/mnt/e/noctria-kingdom-main/airflow_docker/models/openchat-3.5").resolve()
print(f"📦 モデル読み込み中: {model_path}")

# 📁 モデルパスの存在確認
if not model_path.is_dir():
    raise ValueError(f"❌ 指定されたモデルパスが存在しません: {model_path}")

# 🔄 トークナイザーとモデルの読み込み（ローカルファイル限定）
tokenizer = AutoTokenizer.from_pretrained(
    model_path,
    trust_remote_code=True,
    local_files_only=True
)

model = AutoModelForCausalLM.from_pretrained(
    model_path,
    trust_remote_code=True,
    local_files_only=True,
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
)

# モデルを推論モードに
model.eval()
if torch.cuda.is_available():
    model = model.to("cuda")

# リクエストスキーマ
class PromptRequest(BaseModel):
    prompt: str
    max_tokens: int = 256
    temperature: float = 0.7

@app.post("/generate")
async def generate_text(req: PromptRequest):
    try:
        inputs = tokenizer(req.prompt, return_tensors="pt")
        if torch.cuda.is_available():
            inputs = {k: v.to("cuda") for k, v in inputs.items()}

        outputs = model.generate(
            **inputs,
            max_new_tokens=req.max_tokens,
            temperature=req.temperature,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )
        decoded = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return {"response": decoded}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成中にエラーが発生しました: {str(e)}")
