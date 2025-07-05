from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from core.path_config import DATA_DIR
import json
from datetime import datetime
import csv
from io import StringIO

router = APIRouter()
templates = Jinja2Templates(directory=str(DATA_DIR.parent / "noctria_gui" / "templates"))

PUSH_LOG_DIR = DATA_DIR / "push_logs"

# =============================
# 📜 Push履歴一覧ページ
# =============================
@router.get("/push-history", response_class=HTMLResponse)
def push_history(request: Request, keyword: str = "", sort: str = "desc"):
    logs = []

    for path in sorted(PUSH_LOG_DIR.glob("*.json")):
        with open(path, "r", encoding="utf-8") as f:
            log = json.load(f)
            if keyword.lower() in json.dumps(log, ensure_ascii=False).lower():
                logs.append(log)

    logs.sort(key=lambda x: x["timestamp"], reverse=(sort != "asc"))

    return templates.TemplateResponse("push_history.html", {
        "request": request,
        "logs": logs,
        "keyword": keyword,
        "sort": sort,
    })

# =============================
# 📥 CSVエクスポートエンドポイント
# =============================
@router.get("/push-history/export")
def export_push_history_csv():
    fieldnames = ["timestamp", "strategy", "message", "signature"]

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for path in sorted(PUSH_LOG_DIR.glob("*.json")):
        with open(path, "r", encoding="utf-8") as f:
            log = json.load(f)
            row = {
                "timestamp": log.get("timestamp", ""),
                "strategy": log.get("strategy", ""),
                "message": log.get("message", ""),
                "signature": log.get("signature", "")
            }
            writer.writerow(row)

    output.seek(0)
    filename = f"push_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(output, media_type="text/csv", headers={
        "Content-Disposition": f"attachment; filename={filename}"
    })
