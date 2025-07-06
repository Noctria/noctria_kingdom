# routes/statistics_compare.py

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, ACT_LOG_DIR

import os
import json
from datetime import datetime
from collections import defaultdict
import csv
import io

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return None

def load_strategy_logs():
    data = []
    for file in os.listdir(ACT_LOG_DIR):
        if file.endswith(".json"):
            try:
                with open(ACT_LOG_DIR / file, "r", encoding="utf-8") as f:
                    record = json.load(f)
                data.append(record)
            except Exception:
                continue
    return data

def compute_comparison(data, mode, keys, from_date=None, to_date=None):
    result = defaultdict(lambda: {"count": 0, "win_sum": 0, "dd_sum": 0})

    for record in data:
        try:
            date_str = record.get("date")
            if not date_str:
                continue
            date = datetime.strptime(date_str, "%Y-%m-%d")
            if from_date and date < from_date:
                continue
            if to_date and date > to_date:
                continue

            score = record.get("score", {})
            win = score.get("win_rate")
            dd = score.get("max_drawdown")

            if mode == "tag":
                record_keys = record.get("tags", [])
            else:
                record_keys = [record.get("strategy_name")]

            for key in record_keys:
                if key not in keys:
                    continue
                result[key]["count"] += 1
                if isinstance(win, (int, float)):
                    result[key]["win_sum"] += win
                if isinstance(dd, (int, float)):
                    result[key]["dd_sum"] += dd
        except Exception:
            continue

    final = []
    for k, v in result.items():
        count = v["count"]
        avg_win = round(v["win_sum"] / count, 1) if count else 0
        avg_dd = round(v["dd_sum"] / count, 1) if count else 0
        final.append({"key": k, "avg_win": avg_win, "avg_dd": avg_dd, "count": count})

    return sorted(final, key=lambda x: (-x["avg_win"], x["avg_dd"]))

@router.get("/statistics/compare", response_class=HTMLResponse)
async def compare_statistics(request: Request):
    params = request.query_params
    mode = params.get("mode", "tag")
    keys = params.get(mode + "s", "").split(",")
    keys = [k.strip() for k in keys if k.strip()]
    from_date = parse_date(params.get("from"))
    to_date = parse_date(params.get("to"))

    all_data = load_strategy_logs()
    result = compute_comparison(all_data, mode, keys, from_date, to_date)

    return templates.TemplateResponse("statistics_compare.html", {
        "request": request,
        "mode": mode,
        "keys": keys,
        "results": result,
        "filter": {
            "from": params.get("from", ""),
            "to": params.get("to", ""),
        }
    })

@router.get("/statistics/compare/export")
async def export_compare_csv(request: Request):
    params = request.query_params
    mode = params.get("mode", "tag")
    keys = params.get(mode + "s", "").split(",")
    keys = [k.strip() for k in keys if k.strip()]
    from_date = parse_date(params.get("from"))
    to_date = parse_date(params.get("to"))

    all_data = load_strategy_logs()
    result = compute_comparison(all_data, mode, keys, from_date, to_date)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["比較対象", "平均勝率（%）", "平均DD（%）", "件数"])

    for row in result:
        writer.writerow([row["key"], row["avg_win"], row["avg_dd"], row["count"]])

    buffer.seek(0)
    filename = f"compare_export_{mode}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
