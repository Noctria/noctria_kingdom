#!/usr/bin/env python3
# coding: utf-8

"""
📊 /pdca/summary - PDCA再評価の統計サマリ画面
- 再評価ログの統計を表示（core/pdca_log_parser.py に集計処理を委譲）
"""

from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime

from core.path_config import PDCA_LOG_DIR, NOCTRIA_GUI_TEMPLATES_DIR
from core.pdca_log_parser import parse_date_safe, load_and_aggregate_pdca_logs

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

@router.get("/pdca/summary", response_class=HTMLResponse)
async def pdca_summary(
    request: Request,
    from_: str = Query(default=None, alias="from"),
    to: str = Query(default=None),
    mode: str = Query(default="strategy"),  # "strategy" or "tag"
    limit: int = Query(default=20),
):
    # 📆 フィルタ用日付変換
    from_date = parse_date_safe(from_)
    to_date = parse_date_safe(to)

    # 📦 集計処理を共通関数に委譲
    result = load_and_aggregate_pdca_logs(
        log_dir=PDCA_LOG_DIR,
        from_date=from_date,
        to_date=to_date,
        mode=mode,
        limit=limit,
    )

    return templates.TemplateResponse("pdca_summary.html", {
        "request": request,
        "stats": result["stats"],
        "chart": result["chart"],
        "mode": mode,
        "limit": limit,
        "filter": {
            "from": from_ or "",
            "to": to or "",
        }
    })
