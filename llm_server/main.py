import logging
import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from pathlib import Path
from dotenv import load_dotenv

logging.info(
    "LLM flags: enabled=%s mode=%s base=%s model=%s",
    os.getenv("NOCTRIA_LLM_ENABLED"),
    os.getenv("NOCTRIA_HARMONIA_MODE"),
    os.getenv("OPENAI_API_BASE") or os.getenv("OPENAI_BASE_URL"),
    os.getenv("NOCTRIA_GPT_MODEL") or os.getenv("OPENAI_MODEL"),
)

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


# === FastAPI 初期化 ===
app = FastAPI(title="Noctria LLM Server")

# CORS設定（GUIなど外部アクセス時に必要）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適宜制限してください
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

    with open(EVAL_RESULT_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return []

    filtered = []
    for entry in data:
        if (
            isinstance(entry, dict)
            and "filename" in entry
            and "final_capital" in entry
            and "result" in entry
        ):
            filtered.append(StrategyEvaluation(**entry))
    return filtered


def _log_llm_usage(resp):
    """Best-effort logging of OpenAI-like usage fields."""
    try:
        import logging  # local import safe

        u = getattr(resp, "usage", None)
        if u is not None:
            pt = getattr(u, "prompt_tokens", None)
            ct = getattr(u, "completion_tokens", None)
            tt = getattr(u, "total_tokens", None)
            logging.info("LLM usage prompt=%s completion=%s total=%s", pt, ct, tt)
        else:
            logging.info("LLM usage unavailable (provider?)")
    except Exception as _e:
        logging.exception("LLM usage logging failed: %s", _e)
