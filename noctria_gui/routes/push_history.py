from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pathlib import Path

router = APIRouter()
templates = Jinja2Templates(directory="noctria_gui/templates")

PUSH_LOG_DIR = Path("logs/push")  # 例: pushログ保存ディレクトリを指定してください

@router.get("/push/history")
async def push_history(request: Request):
    logs = []
    # ログファイルなどからpush履歴を読み込む処理を実装
    # 例: logs = load_push_logs() またはファイル走査
    # 以下はサンプルの空リストです
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
        # ページネーションや総ページ数を追加するならここに
        "total_pages": 1,
        "current_page": 1
    })

@router.post("/push/trigger")
async def push_trigger(strategy_name: str = Form(...)):
    # 戦略のGitHub Push実行トリガー処理を実装
    # 例: trigger_push(strategy_name)
    # 処理後はpush履歴ページなどへリダイレクト
    return RedirectResponse(url="/push/history", status_code=303)
