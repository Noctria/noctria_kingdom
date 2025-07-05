# noctria_gui/routes/pdca_routes.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from core.path_config import LOGS_DIR
from fastapi.templating import Jinja2Templates
import json
from pathlib import Path

router = APIRouter()
templates = Jinja2Templates(directory=str(LOGS_DIR.parent / "noctria_gui" / "templates"))

@router.get("/pdca-history", response_class=HTMLResponse)
async def pdca_history(request: Request):
    pdca_log_path = LOGS_DIR / "pdca_history.json"
    if pdca_log_path.exists():
        with open(pdca_log_path, "r", encoding="utf-8") as f:
            logs = json.load(f)
    else:
        logs = []

    logs = sorted(logs, key=lambda x: x["timestamp"], reverse=True)
    return templates.TemplateResponse("pdca/history.html", {"request": request, "logs": logs})
