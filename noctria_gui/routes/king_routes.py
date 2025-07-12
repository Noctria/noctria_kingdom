#!/usr/bin/env python3
# coding: utf-8

"""
👑 /king - 中央統治AI NoctriaのAPIルート群
- 評議会の開催（hold_council）
- 評議会ログの保存・取得
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, LOGS_DIR
from core.king_noctria import KingNoctria
from datetime import datetime
import json
from pathlib import Path

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# 評議会ログ保存パス
KING_LOG_PATH = LOGS_DIR / "king_log.json"

def load_logs() -> list:
    if KING_LOG_PATH.exists():
        with open(KING_LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_log(entry: dict):
    logs = load_logs()
    logs.append(entry)
    with open(KING_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)


@router.post("/king/hold-council")
async def hold_council_api(request: Request):
    try:
        data = await request.json()
        king = KingNoctria()
        result = king.hold_council(data)

        # ⏺️ ログとして保存
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "market_data": data,
            "result": result
        }
        save_log(log_entry)

        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@router.get("/king/history", response_class=HTMLResponse)
async def show_king_history(request: Request):
    try:
        logs = load_logs()
        logs = sorted(logs, key=lambda x: x.get("timestamp", ""), reverse=True)
        return templates.TemplateResponse("king_history.html", {
            "request": request,
            "logs": logs
        })
    except Exception as e:
        return templates.TemplateResponse("king_history.html", {
            "request": request,
            "logs": [],
            "error": str(e)
        })
