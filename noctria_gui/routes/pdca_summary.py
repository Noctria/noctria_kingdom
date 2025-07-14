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
from core.path_config import GUI_TEMPLATES_DIR, VERITAS_EVAL_LOG_DIR
from core.pdca_log_parser import load_and_aggregate_pdca_logs

router = APIRouter(prefix="/pdca", tags=["pdca-summary"])
templates = Jinja2Templates(directory=str(GUI_TEMPLATES_DIR))

@router.get("/summary", response_class=HTMLResponse)
async def show_pdca_summary(
    request: Request,
    from_date: str = Query(default=""),
    to_date: str = Query(default="")
):
    # 🔍 日付フィルター用のISO日付オブジェクトに変換（空ならNone）
    try:
        from_dt = datetime.fromisoformat(from_date) if from_date else None
    except ValueError:
        from_dt = None

    try:
        to_dt = datetime.fromisoformat(to_date) if to_date else None
    except ValueError:
        to_dt = None

    # 📥 ログファイルを読み込んで統計を生成（期間指定あり）
    result = load_and_aggregate_pdca_logs(
        log_dir=VERITAS_EVAL_LOG_DIR,
        mode="strategy",  # または "tag"
        limit=20,
        from_date=from_dt,
        to_date=to_dt
    )

    # 📤 テンプレートへ渡す
    return templates.TemplateResponse("pdca_summary.html", {
        "request": request,
        "summary": result["stats"],
        "chart": result["chart"],
        "filter": {
            "from": from_date,
            "to": to_date
        }
    })
