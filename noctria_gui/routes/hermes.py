# noctria_gui/routes/hermes.py

import sys
from pathlib import Path
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

# 必要に応じてsys.pathにsrcの親ディレクトリを追加（環境依存）
sys.path.append(str(Path(__file__).resolve().parents[2]))

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
async def generate_strategy(req: HermesStrategyRequest):
    try:
        prompt = build_prompt(req.symbol, req.tag, req.target_metric)
        code = generate_strategy_code(prompt)
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
        logging.error(f"Hermes生成失敗: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Hermes生成失敗: {str(e)}")
