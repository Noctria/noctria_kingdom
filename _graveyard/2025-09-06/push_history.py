from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pathlib import Path

router = APIRouter(prefix="/push_history")  # prefixを修正

templates = Jinja2Templates(directory="noctria_gui/templates")

PUSH_LOG_DIR = Path("logs/push")  # pushログ保存ディレクトリ

@router.get("/", summary="Push履歴ページ")
async def push_history(request: Request):
    logs = []
    # ログ読み込み処理をここに実装
    filters = {
        "strategy": request.query_params.get("strategy", ""),
        "tag": request.query_params.get("tag", ""),
        "start_date": request.query_params.get("start_date", ""),
        "end_date": request.query_params.get("end_date", ""),
        "sort": request.query_params.get("sort", "desc")
    }
    return templates.TemplateResponse("push_history.html", {
        "request": request,
        "logs": logs,
        "filters": filters,
        "total_pages": 1,
        "current_page": 1
    })

@router.post("/trigger", summary="Pushトリガー")
async def push_trigger(strategy_name: str = Form(...)):
    # Push実行トリガー処理をここに実装
    return RedirectResponse(url="/push_history", status_code=303)
