from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, ACT_LOG_DIR

from datetime import datetime
from pathlib import Path
import os, json, csv, io

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except:
        return None


def load_logs():
    logs = []
    for file in os.listdir(ACT_LOG_DIR):
        if file.endswith(".json"):
            path = Path(ACT_LOG_DIR) / file
            try:
                with open(path, "r", encoding="utf-8") as f:
                    logs.append(json.load(f))
            except:
                continue
    return logs


def filter_and_sort_logs(data, mode, key, sort_by, order):
    filtered = []
    for d in data:
        if mode == "tag":
            if key not in d.get("tags", []):
                continue
        else:
            if d.get("strategy_name") != key:
                continue

        filtered.append({
            "date": d.get("timestamp", "")[:10],
            "win_rate": d.get("scores", {}).get("win_rate"),
            "max_drawdown": d.get("scores", {}).get("max_drawdown")
        })

    reverse = (order == "desc")
    if sort_by in {"win_rate", "max_drawdown"}:
        filtered.sort(key=lambda x: (x[sort_by] is not None, x[sort_by]), reverse=reverse)
    else:
        filtered.sort(key=lambda x: x["date"], reverse=reverse)

    return filtered


@router.get("/", response_class=HTMLResponse)
async def detail_page(request: Request):
    params = request.query_params
    mode = params.get("mode", "strategy")
    key = params.get("key", "")
    sort_by = params.get("sort_by", "date")
    order = params.get("order", "asc")

    all_logs = load_logs()
    results = filter_and_sort_logs(all_logs, mode, key, sort_by, order)

    return templates.TemplateResponse("statistics_detail.html", {
        "request": request,
        "mode": mode,
        "key": key,
        "sort_by": sort_by,
        "order": order,
        "results": results
    })


@router.get("/export")
async def export_csv(request: Request):
    params = request.query_params
    mode = params.get("mode", "strategy")
    key = params.get("key", "")
    sort_by = params.get("sort_by", "date")
    order = params.get("order", "asc")

    all_logs = load_logs()
    results = filter_and_sort_logs(all_logs, mode, key, sort_by, order)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["date", "win_rate", "max_drawdown"])
    writer.writeheader()
    writer.writerows(results)
    output.seek(0)

    filename = f"detail_{key}.csv"

    return StreamingResponse(output, media_type="text/csv", headers={
        "Content-Disposition": f"attachment; filename={filename}"
    })
