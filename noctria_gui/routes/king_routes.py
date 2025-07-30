#!/usr/bin/env python3
# coding: utf-8

"""
👑 /api/king - 中央統治AI NoctriaのAPIルート（統一集約版）
- すべての統治操作（PDCA/戦略生成/再評価/Push/Replay等）を王経由APIに統合
- 統治ID(意思決定ID)の一元管理、王ログ保存・取得
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, LOGS_DIR
from src.core.king_noctria import KingNoctria

from datetime import datetime
from pathlib import Path
import json
import uuid

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

@router.post("/command")
async def king_command_api(request: Request):
    """
    👑 王Noctriaによる統治コマンドAPI（すべてのPDCA/DAG/AI指令をここに統合）
    例: {"command": "recheck", "args": {...}, "ai": "veritas"}
    """
    try:
        data = await request.json()
        command = data.get("command")
        args = data.get("args", {})
        ai = data.get("ai", None)
        decision_id = f"KC-{uuid.uuid4()}"
        
        king = KingNoctria()

        # --- 王の采配で各コマンドに対応（臣下AI/DAG等の一元采配） ---
        if command == "council":
            result = king.hold_council(args)
        elif command == "generate_strategy":
            result = king.generate_strategy(args)
        elif command == "evaluate":
            result = king.evaluate(args)
        elif command == "recheck":
            result = king.recheck(args)
        elif command == "push":
            result = king.push(args)
        elif command == "replay":
            result = king.replay(args)
        else:
            return JSONResponse(content={"error": f"未知コマンド: {command}"}, status_code=400)
        
        log_entry = {
            "decision_id": decision_id,
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "args": args,
            "ai": ai,
            "result": result
        }
        save_log(log_entry)
        result["decision_id"] = decision_id  # 統治ID付与
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            content={"error": f"King command failed: {str(e)}"},
            status_code=500
        )

@router.get("/history", response_class=HTMLResponse)
async def show_king_history(request: Request):
    """
    📜 KingNoctriaによる過去の評議会（全統治コマンド）履歴GUI
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
