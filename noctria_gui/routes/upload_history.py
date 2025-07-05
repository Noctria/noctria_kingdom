from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
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
