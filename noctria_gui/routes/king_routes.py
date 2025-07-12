#!/usr/bin/env python3
# coding: utf-8

"""
👑 KingNoctria 統治APIルート
- 五臣会議（hold_council）をトリガー
- 現在の統治判断（ステータス）や履歴を返す
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from datetime import datetime
import json
from core.path_config import LOGS_DIR, NOCTRIA_GUI_TEMPLATES_DIR
from core.king_noctria import KingNoctria

router = APIRouter(prefix="/king", tags=["KingNoctria 統治API"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

KING_LOG_PATH = LOGS_DIR / "king_log.json"
_last_council_result = None


class MarketData(BaseModel):
    price: float
    previous_price: float
    volume: float
    spread: float
    order_block: float
    volatility: float
    trend_prediction: str
    sentiment: float
    trend_strength: float
    liquidity_ratio: float
    momentum: float
    short_interest: float


@router.post("/hold-council")
async def hold_council(market: MarketData):
    global _last_council_result
    try:
        king = KingNoctria()
        result = king.hold_council(market.dict())
        _last_council_result = result

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "market": market.dict(),
            "decision": result
        }

        if KING_LOG_PATH.exists():
            with open(KING_LOG_PATH, "r", encoding="utf-8") as f:
                logs = json.load(f)
        else:
            logs = []

        logs.append(log_entry)

        with open(KING_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)

        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/status")
async def get_latest_status():
    if _last_council_result:
        return JSONResponse(content=_last_council_result)
    else:
        return JSONResponse(status_code=404, content={"error": "No council result available"})


@router.get("/history", response_class=HTMLResponse)
async def view_king_history(request: Request):
    logs = []

    if KING_LOG_PATH.exists():
        try:
            with open(KING_LOG_PATH, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            logs = []

    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    return templates.TemplateResponse("king_history.html", {
        "request": request,
        "logs": logs
    })
