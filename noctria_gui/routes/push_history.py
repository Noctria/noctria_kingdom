from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from noctria_gui.services import push_history_service

router = APIRouter()
templates = Jinja2Templates(directory="noctria_gui/templates")

@router.get("/push-history", response_class=HTMLResponse)
async def push_history_view(request: Request, sort: str = "desc", keyword: str = ""):
    logs = push_history_service.load_push_logs()

    # キーワードフィルター
    if keyword:
        logs = [
            log for log in logs
            if keyword.lower() in log.get("strategy", "").lower()
            or keyword.lower() in log.get("message", "").lower()
        ]

    # 日時ソート
    reverse = sort != "asc"
    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=reverse)

    return templates.TemplateResponse("push_history.html", {
        "request": request,
        "logs": logs,
        "sort": sort,
        "keyword": keyword,
    })
