import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

# === FastAPI 初期化 ===
app = FastAPI(title="Noctria LLM Server")

# CORS（GUIなど外部からアクセスする場合に必要）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番運用では限定すべき
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === 評価結果データ構造 ===
class StrategyEvaluation(BaseModel):
    filename: str
    final_capital: float
    result: str  # "✅ 採用" or "❌ 不採用"

# === ファイルパス設定 ===
EVAL_RESULT_PATH = "/noctria_kingdom/airflow_docker/logs/veritas_eval_result.json"

# === APIエンドポイント ===

@app.get("/")
def read_root():
    return {"message": "🧠 Noctria LLMサーバー起動中"}

@app.get("/veritas/eval_results", response_model=List[StrategyEvaluation])
def get_veritas_eval_results():
    """
    Veritas による評価結果（veritas_eval_result.json）を返す。
    GUIや監視ダッシュボードから可視化可能。
    """
    if not os.path.exists(EVAL_RESULT_PATH):
        return []

    with open(EVAL_RESULT_PATH, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return []

    # 必要なフィールドだけ抽出
    filtered = []
    for entry in data:
        if "filename" in entry and "final_capital" in entry and "result" in entry:
            filtered.append(StrategyEvaluation(**entry))
    return filtered
