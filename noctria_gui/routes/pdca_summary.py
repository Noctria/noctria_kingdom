#!/usr/bin/env python3
# coding: utf-8

"""
📊 /pdca/summary - PDCA再評価の統計ダッシュボード
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, LOGS_DIR
import json

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

@router.get("/pdca/summary", response_class=HTMLResponse)
async def show_pdca_summary(request: Request):
    eval_log_path = LOGS_DIR / "veritas_eval_result.json"

    if not eval_log_path.exists():
        return templates.TemplateResponse("pdca_summary.html", {
            "request": request,
            "stats": {},
            "chart": {"labels": [], "data": []},
        })

    with open(eval_log_path, "r", encoding="utf-8") as f:
        logs = json.load(f)

    win_diffs = []
    dd_diffs = []
    adopted_count = 0
    win_improved = 0
    dd_improved = 0
    labels = []
    win_diff_values = []

    for log in logs:
        before = log.get("win_rate_before")
        after = log.get("win_rate_after")
        dd_before = log.get("max_dd_before")
        dd_after = log.get("max_dd_after")
        strategy = log.get("strategy", "N/A")
        status = log.get("status", "")

        if status == "adopted":
            adopted_count += 1

        if before is not None and after is not None:
            diff = round(after - before, 2)
            win_diffs.append(diff)
            if diff > 0:
                win_improved += 1
            labels.append(strategy)
            win_diff_values.append(diff)

        if dd_before is not None and dd_after is not None:
            dd_diff = round(dd_before - dd_after, 2)
            dd_diffs.append(dd_diff)
            if dd_diff > 0:
                dd_improved += 1

    avg_win_diff = round(sum(win_diffs) / len(win_diffs), 2) if win_diffs else 0.0
    avg_dd_diff = round(sum(dd_diffs) / len(dd_diffs), 2) if dd_diffs else 0.0

    chart_data = {
        "labels": labels,
        "data": win_diff_values,
    }

    stats = {
        "avg_win_rate_diff": avg_win_diff,
        "avg_dd_diff": avg_dd_diff,
        "win_rate_improved": win_improved,
        "dd_improved": dd_improved,
        "adopted": adopted_count,
    }

    return templates.TemplateResponse("pdca_summary.html", {
        "request": request,
        "stats": stats,
        "chart": chart_data,
    })
