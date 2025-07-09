#!/usr/bin/env python3
# coding: utf-8

"""
📊 /pdca/summary - PDCA再評価の統計サマリ画面
- 再評価結果ログを集計し、改善率や採用数を表示
- 📅 期間指定（from～to）によるフィルタに対応
"""

from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
from pathlib import Path
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
    to: str = Query(default=None)
):
    from_date = parse_date_safe(from_)
    to_date = parse_date_safe(to)

    results = []
    for file in sorted(PDCA_LOG_DIR.glob("*.json")):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)

            recheck_ts = data.get("recheck_timestamp")
            if not recheck_ts:
                continue

            ts = datetime.strptime(recheck_ts, "%Y-%m-%dT%H:%M:%S")
            if from_date and ts < from_date:
                continue
            if to_date and ts > to_date:
                continue

            results.append({
                "strategy": data.get("strategy"),
                "win_rate_before": data.get("win_rate_before"),
                "win_rate_after": data.get("win_rate_after"),
                "diff": round(data.get("win_rate_after", 0) - data.get("win_rate_before", 0), 2),
                "max_dd_before": data.get("max_dd_before"),
                "max_dd_after": data.get("max_dd_after"),
                "dd_diff": round(data.get("max_dd_before", 0) - data.get("max_dd_after", 0), 2),
                "status": data.get("status", "unknown")
            })
        except Exception:
            continue

    # 📊 統計値集計
    win_diffs = [r["diff"] for r in results]
    dd_diffs = [r["dd_diff"] for r in results]

    stats = {
        "avg_win_rate_diff": round(sum(win_diffs) / len(win_diffs), 2) if win_diffs else 0.0,
        "avg_dd_diff": round(sum(dd_diffs) / len(dd_diffs), 2) if dd_diffs else 0.0,
        "win_rate_improved": sum(1 for r in results if r["diff"] > 0),
        "dd_improved": sum(1 for r in results if r["dd_diff"] > 0),
        "adopted": sum(1 for r in results if r["status"] == "adopted"),
        "detail": results,
    }

    return templates.TemplateResponse("pdca_summary.html", {
        "request": request,
        "stats": stats,
        "chart": {
            "labels": [r["strategy"] for r in results],
            "data": [r["diff"] for r in results],
            "dd_data": [r["dd_diff"] for r in results],
        },
        "filter": {
            "from": from_ or "",
            "to": to or "",
        }
    })
