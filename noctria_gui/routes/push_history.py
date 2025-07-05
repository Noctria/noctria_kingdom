from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pathlib import Path
from core.path_config import PUSH_LOG_DIR
from noctria_gui.services.push_history_service import load_push_logs

router = APIRouter()

@router.get("/push-history", response_class=HTMLResponse)
async def show_push_history(request: Request, sort: str = "desc"):
    """
    📜 GitHub Push履歴一覧ページ
    - ソート: asc（昇順）/desc（降順）
    """
    logs = load_push_logs(sort=sort)
    return request.app.state.templates.TemplateResponse("push_history.html", {
        "request": request,
        "logs": logs,
        "sort": sort,
    })
