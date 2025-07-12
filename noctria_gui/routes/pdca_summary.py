#!/usr/bin/env python3
# coding: utf-8

"""
📊 /pdca/summary - PDCA再評価の統計サマリ画面
- 再評価結果ログを集計し、改善率や採用数を表示
"""

from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import json

from core.path_config import PDCA_LOG_DIR, NOCTRIA_GUI_TEMPLATES_DIR

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


def parse_date_safe(date_str: str) -> datetime | None:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return None


@router.get("/pdca/summary", response_class=HTMLResponse)
async def pdca_summary(
    request: Request,
    from_: str = Query(default=None, alias="from"),
    to: str = Query(default=None),
    mode: str = Query(default="strategy"),  # "strategy" or "tag"
    limit: int = Query(default=20),
):
    from_date = parse_date_safe(from_)
    to_date = parse_date_safe(to)

    raw_results = []
    for file in sorted(PDCA_LOG_DIR.glob("*.json")):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)

            recheck_ts = data.get("recheck_timestamp")
            if not recheck_ts:
                continue

            try:
                ts = datetime.strptime(recheck_ts, "%Y-%m-%dT%H:%M:%S")
            except Exception:
                continue

            if from_date and ts < from_date:
                continue
            if to_date and ts > to_date:
                continue

            win_before = float(data.get("win_rate_before", 0.0))
            win_after = float(data.get("win_rate_after", 0.0))
            dd_before = float(data.get("max_dd_before", 0.0))
            dd_after = float(data.get("max_dd_after", 0.0))

            raw_results.append({
                "strategy": data.get("strategy"),
                "tag": data.get("tag", "unknown"),
                "win_rate_before": win_before,
                "win_rate_after": win_after,
                "diff": round(win_after - win_before, 2),
                "max_dd_before": dd_before,
                "max_dd_after": dd_after,
                "dd_diff": round(dd_before - dd_after, 2),
                "status": data.get("status", "unknown")
            })
        except Exception:
            continue

    group_key = "strategy" if mode == "strategy" else "tag"
    grouped = defaultdict(list)
    for r in raw_results:
        key = r.get(group_key) or "unknown"
        grouped[key].append(r)

    detail_rows = []
    for key, group in grouped.items():
        win_before_vals = [float(g.get("win_rate_before", 0.0)) for g in group]
        win_after_vals = [float(g.get("win_rate_after", 0.0)) for g in group]
        dd_before_vals = [float(g.get("max_dd_before", 0.0)) for g in group]
        dd_after_vals = [float(g.get("max_dd_after", 0.0)) for g in group]

        avg_win_rate_before = sum(win_before_vals) / len(group)
        avg_win_rate_after = sum(win_after_vals) / len(group)
        avg_diff = round(avg_win_rate_after - avg_win_rate_before, 2)

        avg_dd_before = sum(dd_before_vals) / len(group)
        avg_dd_after = sum(dd_after_vals) / len(group)
        dd_diff = round(avg_dd_before - avg_dd_after, 2)

        adopted = any(g.get("status") == "adopted" for g in group)

        detail_rows.append({
            "strategy": key,
            "win_rate_before": round(avg_win_rate_before, 2),
            "win_rate_after": round(avg_win_rate_after, 2),
            "diff": avg_diff,
            "max_dd_before": round(avg_dd_before, 2),
            "max_dd_after": round(avg_dd_after, 2),
            "status": "adopted" if adopted else "pending",
        })

    detail_rows.sort(key=lambda x: x["diff"], reverse=True)
    limited_rows = detail_rows[:limit]

    chart_labels = [r["strategy"] for r in limited_rows]
    chart_data = [r["diff"] for r in limited_rows]
    chart_dd_data = [
        round(r["max_dd_before"] - r["max_dd_after"], 2)
        for r in limited_rows
    ]

    all_diffs = [r["diff"] for r in raw_results]
    all_dd_diffs = [r["dd_diff"] for r in raw_results]

    stats = {
        "avg_win_rate_diff": round(sum(all_diffs) / len(all_diffs), 2) if all_diffs else 0.0,
        "avg_dd_diff": round(sum(all_dd_diffs) / len(all_dd_diffs), 2) if all_dd_diffs else 0.0,
        "win_rate_improved": sum(1 for r in raw_results if r["diff"] > 0),
        "dd_improved": sum(1 for r in raw_results if r["dd_diff"] > 0),
        "adopted": sum(1 for r in raw_results if r["status"] == "adopted"),
        "detail": limited_rows,
    }

    return templates.TemplateResponse("pdca_summary.html", {
        "request": request,
        "stats": stats,
        "mode": mode,
        "limit": limit,
        "chart": {
            "labels": chart_labels,
            "data": chart_data,
            "dd_data": chart_dd_data,
        },
        "filter": {
            "from": from_ or "",
            "to": to or "",
        }
    })
