#!/usr/bin/env python3
# coding: utf-8

"""
👑 /api/king - 中央統治AI NoctriaのAPIルート（理想形・decision_id一元管理）
- 全てのコマンドは「王本体でdecision_id発行・全統治履歴に保存」
- APIはその橋渡しに徹する
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, LOGS_DIR
from src.core.king_noctria import KingNoctria

from datetime import datetime
from pathlib import Path
import json
import logging

router = APIRouter(prefix="/api/king", tags=["King"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

KING_LOG_PATH = LOGS_DIR / "king_log.jsonl"  # 1行1レコード型を推奨

logger = logging.getLogger("king_routes")

def load_logs() -> list:
    try:
        if KING_LOG_PATH.exists():
            with open(KING_LOG_PATH, "r", encoding="utf-8") as f:
                return [json.loads(line) for line in f if line.strip()]
        return []
    except Exception as e:
        logger.error(f"🔴 load_logs失敗: {e}")
        return []

@router.post("/command")
async def king_command_api(request: Request):
    """
    👑 王Noctriaによる統治コマンドAPI（全PDCA/DAG/AI指令を統一集約）
    """
    try:
        data = await request.json()
        command = data.get("command")
        args = data.get("args", {})
        ai = data.get("ai", None)  # 現状使われていないが将来対応用に保持
        caller = "king_routes"
        reason = data.get("reason", f"APIコマンド[{command}]実行")
        
        king = KingNoctria()

        # --- 王の采配で各コマンドに対応 ---
        # すべて「decision_idは王本体で発行」
        if command == "council":
            result = king.hold_council(args, caller=caller, reason=reason)
        elif command == "generate_strategy":
            result = king.trigger_generate(args, caller=caller, reason=reason)
        elif command == "evaluate":
            result = king.trigger_eval(args, caller=caller, reason=reason)
        elif command == "recheck":
            result = king.trigger_recheck(args, caller=caller, reason=reason)
        elif command == "push":
            result = king.trigger_push(args, caller=caller, reason=reason)
        elif command == "replay":
            log_path = args.get("log_path", "") if isinstance(args, dict) else ""
            result = king.trigger_replay(log_path, caller=caller, reason=reason)
        else:
            return JSONResponse(content={"error": f"未知コマンド: {command}"}, status_code=400)

        # ここで王本体のdecision_idが返ってきているはず
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"King command failed: {e}", exc_info=True)
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
        logger.error(f"ログ読み込みエラー: {e}", exc_info=True)
        return templates.TemplateResponse("king_history.html", {
            "request": request,
            "logs": [],
            "error": f"ログ読み込みエラー: {str(e)}"
        })
