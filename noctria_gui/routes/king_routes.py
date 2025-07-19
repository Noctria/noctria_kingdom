#!/usr/bin/env python3
# coding: utf-8

"""
👑 /api/king - 中央統治AI NoctriaのAPIルート
- 評議会の開催（/api/king/council）
- 評議会ログの保存・取得（/api/king/history）
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, LOGS_DIR
from src.core.king_noctria import KingNoctria

from datetime import datetime
from pathlib import Path
import json

router = APIRouter(prefix="/api/king", tags=["King"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

KING_LOG_PATH = LOGS_DIR / "king_log.json"

def load_logs() -> list:
    try:
        if KING_LOG_PATH.exists():
            with open(KING_LOG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"🔴 load_logs失敗: {e}")
        return []

def save_log(entry: dict):
    try:
        logs = load_logs()
        logs.append(entry)
        with open(KING_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"🔴 save_log失敗: {e}")

@router.post("/council")
async def hold_council_api(request: Request):
    """
    🧠 KingNoctriaによる評議会の開催（POSTされたmarket_dataでhold_council）
    """
    try:
        data = await request.json()
        if not isinstance(data, dict):
            return JSONResponse(content={"error": "market_dataが不正です"}, status_code=400)

        king = KingNoctria()
        result = king.hold_council(data)

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "market_data": data,
            "result": result
        }
        save_log(log_entry)

        return JSONResponse(content=result)

    except Exception as e:
        return JSONResponse(
            content={"error": f"Council failed: {str(e)}"},
            status_code=500
        )

@router.get("/history", response_class=HTMLResponse)
async def show_king_history(request: Request):
    """
    📜 KingNoctriaによる過去の評議会履歴GUI
    """
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
            "error": f"ログ読み込みエラー: {str(e)}"
        })
