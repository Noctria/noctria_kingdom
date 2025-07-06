# routes/statistics_detail.py

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, ACT_LOG_DIR

from datetime import datetime
from pathlib import Path
import json

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

def parse_date_safe(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except:
        return None

@router.get("/statistics/detail", response_class=HTMLResponse)
async def detail_view(request: Request, mode: str = "tag", key: str = ""):
    if mode not in ("tag", "strategy"):
        raise HTTPException(status_code=400, detail="Invalid mode")

    records = []
    for path in ACT_LOG_DIR.glob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as f:
                record = json.load(f)
            date = parse_date_safe(record.get("date"))
            if not date:
                continue

            if mode == "strategy" and record.get("strategy_name") == key:
                records.append((date, record))
            elif mode == "tag" and key in record.get("tags", []):
                records.append((date, record))
        except:
            continue

    records.sort(key=lambda x: x[0])
    results = []
    for date, record in records:
        score = record.get("score", {})
        results.append({
            "date": date.strftime("%Y-%m-%d"),
            "win_rate": score.get("win_rate"),
            "max_drawdown": score.get("max_drawdown")
        })

    return templates.TemplateResponse("statistics_detail.html", {
        "request": request,
        "mode": mode,
        "key": key,
        "results": results
    })
