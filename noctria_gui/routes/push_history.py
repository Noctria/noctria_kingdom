from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json
import csv
import io
from core.path_config import PUSH_LOG_DIR
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="noctria_gui/templates")


@router.get("/push-history", response_class=HTMLResponse)
def view_push_history(request: Request, sort: str = "desc", keyword: str = ""):
    logs = []

    if not PUSH_LOG_DIR.exists():
        PUSH_LOG_DIR.mkdir(parents=True)

    for file in sorted(PUSH_LOG_DIR.glob("*.json")):
        with open(file, "r", encoding="utf-8") as f:
            log = json.load(f)
            if keyword.lower() in log.get("strategy", "").lower():
                logs.append(log)

    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=(sort == "desc"))

    return templates.TemplateResponse("push_history.html", {
        "request": request,
        "logs": logs,
        "sort": sort,
        "keyword": keyword
    })


@router.get("/push-history/export")
def export_push_history_csv():
    fieldnames = ["timestamp", "strategy", "message", "signature"]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for file in sorted(PUSH_LOG_DIR.glob("*.json")):
        with open(file, "r", encoding="utf-8") as f:
            log = json.load(f)
            writer.writerow({
                "timestamp": log.get("timestamp", ""),
                "strategy": log.get("strategy", ""),
                "message": log.get("message", ""),
                "signature": log.get("signature", "")
            })

    output.seek(0)
    filename = f"push_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(output, media_type="text/csv", headers={
        "Content-Disposition": f"attachment; filename={filename}"
    })


@router.get("/push-history/detail", response_class=HTMLResponse)
def push_history_detail(request: Request, timestamp: str):
    log_path = PUSH_LOG_DIR / f"{timestamp}.json"
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="Log not found")

    with open(log_path, "r", encoding="utf-8") as f:
        log = json.load(f)

    return templates.TemplateResponse("push_history_detail.html", {
        "request": request,
        "log": log
    })
