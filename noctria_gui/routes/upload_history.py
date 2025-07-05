from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from noctria_gui.services.upload_actions import re_evaluate_strategy, delete_strategy_log
from pathlib import Path

router = APIRouter()
templates = Jinja2Templates(directory="noctria_gui/templates")

UPLOAD_LOG_DIR = Path("logs/uploads")

@router.get("/upload-history", response_class=HTMLResponse)
def show_upload_history(request: Request):
    histories = []
    for subdir in sorted(UPLOAD_LOG_DIR.iterdir(), reverse=True):
        if subdir.is_dir():
            record = {"id": subdir.name, "files": []}
            for file in subdir.glob("*"):
                content = file.read_text(encoding="utf-8")
                record["files"].append({"name": file.name, "content": content})
            histories.append(record)

    return templates.TemplateResponse("upload_history.html", {
        "request": request,
        "histories": histories
    })

@router.post("/upload-history/re-evaluate", response_class=RedirectResponse)
def post_re_evaluate(strategy_id: str = Form(...)):
    re_evaluate_strategy(strategy_id)
    return RedirectResponse(url="/upload-history", status_code=303)

@router.post("/upload-history/delete", response_class=RedirectResponse)
def post_delete(strategy_id: str = Form(...)):
    delete_strategy_log(strategy_id)
    return RedirectResponse(url="/upload-history", status_code=303)
