# noctria_gui/routes/hermes.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

# Hermes戦略生成AIの呼び出し（srcパスの調整は要環境依存。sys.path追記等は必要に応じて）
from src.hermes.strategy_generator import build_prompt, generate_strategy_code, save_to_file, save_to_db

router = APIRouter()

class HermesStrategyRequest(BaseModel):
    symbol: str
    tag: str
    target_metric: str

class HermesStrategyResponse(BaseModel):
    status: str
    strategy_code: str
    explanation: Optional[str] = None
    prompt: str
    saved_path: Optional[str] = None

@router.post("/hermes/generate_strategy", response_model=HermesStrategyResponse)
def generate_strategy(req: HermesStrategyRequest):
    try:
        prompt = build_prompt(req.symbol, req.tag, req.target_metric)
        code = generate_strategy_code(prompt)
        # 今後explanationもHermesで自動生成可能。ここはプレースホルダ
        explanation = f"Hermes生成戦略：{req.symbol} / {req.tag} / {req.target_metric}"
        save_path = save_to_file(code, req.tag)
        save_to_db(prompt, code)
        return HermesStrategyResponse(
            status="SUCCESS",
            strategy_code=code,
            explanation=explanation,
            prompt=prompt,
            saved_path=save_path
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hermes生成失敗: {str(e)}")
