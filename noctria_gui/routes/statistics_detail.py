# routes/statistics_detail.py

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, ACT_LOG_DIR
from collections import defaultdict
from statistics import mean, median
import os, json
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except:
        return None

def load_logs():
    data = []
    for file in os.listdir(ACT_LOG_DIR):
        if file.endswith(".json"):
            try:
                with open(os.path.join(ACT_LOG_DIR, file)) as f:
                    data.append(json.load(f))
            except:
                continue
    return data

@router.get("/statistics/detail", response_class=HTMLResponse)
async def statistics_detail(request: Request):
    logs = load_logs()

    metric_values = defaultdict(list)
    for log in logs:
        for metric, value in log.get("scores", {}).items():
            metric_values[metric].append(value)

    summary = {
        metric: {
            "mean": round(mean(values), 4),
            "median": round(median(values), 4),
            "count": len(values),
            "values": sorted(values),
        }
        for metric, values in metric_values.items()
        if values
    }

    return templates.TemplateResponse("statistics_detail.html", {
        "request": request,
        "summary": summary,
    })
