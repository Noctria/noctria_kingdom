# routes/dashboard.py

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, ACT_LOG_DIR, PUSH_LOG_DIR, PDCA_LOG_DIR

from collections import defaultdict
from datetime import datetime
import json
import os
import io
import csv

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


def load_logs_filtered(log_dir, from_date=None, to_date=None, tag_keyword=None):
    counter = defaultdict(int)
    win_rate_data = defaultdict(list)
    dd_data = defaultdict(list)

    for file in os.listdir(log_dir):
        if not file.endswith(".json"):
            continue
        try:
            with open(os.path.join(log_dir, file), "r", encoding="utf-8") as f:
                data = json.load(f)

            date_str = data.get("date")
            if not date_str:
                continue
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")

            if from_date and date_obj < from_date:
                continue
            if to_date and date_obj > to_date:
                continue
            if tag_keyword:
                tags = data.get("tags", [])
                if not any(tag_keyword.lower() in t.lower() for t in tags):
                    continue

            key = date_obj.strftime("%Y-%m-%d")
            counter[key] += 1

            score = data.get("score", {})
            win = score.get("win_rate")
            dd = score.get("max_drawdown")
            if isinstance(win, (int, float)):
                win_rate_data[key].append(win)
            if isinstance(dd, (int, float)):
                dd_data[key].append(dd)

        except Exception:
            continue

    return counter, win_rate_data, dd_data


def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return None


def compute_stats(from_date, to_date, tag_keyword):
    act_counter, win_rate_data, dd_data = load_logs_filtered(
        str(ACT_LOG_DIR), from_date, to_date, tag_keyword
    )
    push_counter, _, _ = load_logs_filtered(str(PUSH_LOG_DIR), from_date, to_date)
    pdca_counter, _, _ = load_logs_filtered(str(PDCA_LOG_DIR), from_date, to_date)

    all_dates = sorted(set(act_counter) | set(push_counter) | set(win_rate_data) | set(dd_data))
    promoted_values = [act_counter.get(d, 0) for d in all_dates]
    pushed_values = [push_counter.get(d, 0) for d in all_dates]
    avg_win_rates = [
        round(sum(win_rate_data[d]) / len(win_rate_data[d]), 1) if d in win_rate_data else None
        for d in all_dates
    ]
    avg_max_dds = [
        round(sum(dd_data[d]) / len(dd_data[d]), 1) if d in dd_data else None
        for d in all_dates
    ]

    avg_win = sum(w for w in avg_win_rates if w is not None) / max(len([w for w in avg_win_rates if w is not None]), 1)

    return {
        "promoted_count": sum(promoted_values),
        "push_count": sum(pushed_values),
        "pdca_count": sum(pdca_counter.values()),
        "avg_win_rate": avg_win,
        "dates": all_dates,
        "promoted_values": promoted_values,
        "pushed_values": pushed_values,
        "avg_win_rates": avg_win_rates,
        "avg_max_dds": avg_max_dds,
    }


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    params = request.query_params
    from_date = parse_date(params.get("from"))
    to_date = parse_date(params.get("to"))
    tag_keyword = params.get("tag")

    stats = compute_stats(from_date, to_date, tag_keyword)
    stats["filter"] = {
        "from": params.get("from") or "",
        "to": params.get("to") or "",
        "tag": tag_keyword or ""
    }

    return templates.TemplateResponse("dashboard.html", {"request": request, "stats": stats})


@router.get("/dashboard/export")
async def export_dashboard_csv(request: Request):
    params = request.query_params
    from_date = parse_date(params.get("from"))
    to_date = parse_date(params.get("to"))
    tag_keyword = params.get("tag")

    stats = compute_stats(from_date, to_date, tag_keyword)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["日付", "昇格戦略数", "Push完了数", "平均勝率（%）", "最大DD（%）"])

    for i, date in enumerate(stats["dates"]):
        writer.writerow([
            date,
            stats["promoted_values"][i],
            stats["pushed_values"][i],
            stats["avg_win_rates"][i] if stats["avg_win_rates"][i] is not None else "",
            stats["avg_max_dds"][i] if stats["avg_max_dds"][i] is not None else ""
        ])

    buffer.seek(0)
    filename = f"dashboard_export.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
