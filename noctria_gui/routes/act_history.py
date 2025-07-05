from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import json
from pathlib import Path

from core.path_config import ACT_LOG_DIR, NOCTRIA_GUI_TEMPLATES_DIR

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# ========================================
# 📜 /act-history - 採用戦略の記録閲覧ページ
# ========================================
@router.get("/act-history", response_class=HTMLResponse)
async def show_act_history(request: Request):
    log_files = sorted(ACT_LOG_DIR.glob("*.json"), reverse=True)
    logs = []

    for log_file in log_files:
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                logs.append(data)
        except Exception as e:
            print(f"⚠️ ログ読み込み失敗: {log_file} - {e}")

    return templates.TemplateResponse("act_history.html", {
        "request": request,
        "logs": logs,
    })
