from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json
from core.path_config import DATA_DIR

router = APIRouter()
templates = Jinja2Templates(directory=str(DATA_DIR.parent / "noctria_gui" / "templates"))

ACT_LOG_DIR = DATA_DIR / "act_logs"

@router.get("/act-history", response_class=HTMLResponse)
async def act_history(request: Request, pushed: str = None):
    logs = []
    for file in sorted(ACT_LOG_DIR.glob("*.json"), reverse=True):
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
            logs.append(data)

    # 🔍 pushed フィルタ適用（true/false）
    if pushed is not None:
        pushed_bool = pushed.lower() == "true"
        logs = [log for log in logs if log.get("pushed") == pushed_bool]

    return templates.TemplateResponse("act_history.html", {
        "request": request,
        "logs": logs,
        "pushed_filter": pushed,
    })
