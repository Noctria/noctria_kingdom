# noctria_gui/routes/hermes.py

import sys
from pathlib import Path
import logging
import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

src_path = str(Path(__file__).resolve().parents[2])
if src_path not in sys.path:
    sys.path.insert(0, src_path)  # insertが望ましい（優先度高い）

from src.hermes.strategy_generator import build_prompt, generate_strategy_code, save_to_file, save_to_db

router = APIRouter()
logger = logging.getLogger("noctria.hermes")

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
        code = await asyncio.to_thread(generate_strategy_code, prompt)
        explanation = f"Hermes生成戦略：{req.symbol} / {req.tag} / {req.target_metric}"
        # ファイル保存とDB保存も非同期化可能
        save_path = await asyncio.to_thread(save_to_file, code, req.tag)
        await asyncio.to_thread(save_to_db, prompt, code)
        return HermesStrategyResponse(
            status="SUCCESS",
            strategy_code=code,
            explanation=explanation,
            prompt=prompt,
            saved_path=save_path
        )
    except Exception as e:
        logger.error(f"Hermes生成失敗: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Hermes生成失敗: {str(e)}")
