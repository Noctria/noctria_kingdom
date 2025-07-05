from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, LOGS_DIR
from pathlib import Path
import json

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

PUSH_HISTORY_LOG = LOGS_DIR / "github_push_history.json"

@router.get("/push-history")
async def show_push_history(request: Request):
    logs = []

    if PUSH_HISTORY_LOG.exists():
        with open(PUSH_HISTORY_LOG, "r", encoding="utf-8") as f:
            try:
                logs = json.load(f)
            except json.JSONDecodeError:
                logs = []

    return templates.TemplateResponse("push_history.html", {
        "request": request,
        "logs": logs,
    })
