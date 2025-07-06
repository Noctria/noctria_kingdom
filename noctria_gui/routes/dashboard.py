# routes/dashboard.py

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, ACT_LOG_DIR, PUSH_LOG_DIR, PDCA_LOG_DIR

from collections import defaultdict
from datetime import datetime
import json
import os

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


def load_logs_by_date(log_dir, extract_score=False):
    counter = defaultdict(int)
    win_rate_data = defaultdict(list)
    dd_data = defaultdict(list)

    for file in os.listdir(log_dir):
        if file.endswith(".json"):
            with open(os.path.join(log_dir, file), "r", encoding="utf-8") as f:
                data = json.load(f)
                date_str = data.get("date")
                if date_str:
                    try:
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                        key = date_obj.strftime("%Y-%m-%d")
                        counter[key] += 1

                        if extract_score:
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


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    act_counter, win_rate_data, dd_data = load_logs_by_date(str(ACT_LOG_DIR), extract_score=True)
    push_counter, _, _ = load_logs_by_date(str(PUSH_LOG_DIR))
    pdca_counter, _, _ = load_logs_by_date(str(PDCA_LOG_DIR))

    all_dates = sorted(set(act_counter.keys()) | set(push_counter.keys()) | set(win_rate_data.keys()) | set(dd_data.keys()))
    promoted_values = [act_counter.get(d, 0) for d in all_dates]
    pushed_values = [push_counter.get(d, 0) for d in all_dates]

    avg_win_rates = [
        round(sum(win_rate_data[d])/len(win_rate_data[d]), 1) if d in win_rate_data else None
        for d in all_dates
    ]
    avg_max_dds = [
        round(sum(dd_data[d])/len(dd_data[d]), 1) if d in dd_data else None
        for d in all_dates
    ]

    flat_win_rates = [w for w in avg_win_rates if w is not None]
    avg_win = sum(flat_win_rates) / len(flat_win_rates) if flat_win_rates else 0

    stats = {
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

    return templates.TemplateResponse("dashboard.html", {"request": request, "stats": stats})
