#!/usr/bin/env python3
# coding: utf-8

"""
📊 PDCA Summary Route (v2.0+)
- PDCA再評価の統計サマリ画面
- 再評価結果ログを集計し、改善率や採用数を表示
"""

import logging
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
from typing import Optional

from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, PDCA_LOG_DIR
from src.core.pdca_log_parser import load_and_aggregate_pdca_logs

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

router = APIRouter(prefix="/pdca", tags=["pdca-summary"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

@router.get("/summary", response_class=HTMLResponse)
async def show_pdca_summary(
    request: Request,
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    mode: str = Query(default="strategy"),
    limit: int = Query(default=20)
):
    logging.info(f"PDCAサマリーの閲覧要求: mode={mode}, 期間={from_date}~{to_date}")

    from_dt, to_dt = None, None
    try:
        if from_date: from_dt = datetime.fromisoformat(from_date)
        if to_date: to_dt = datetime.fromisoformat(to_date)
    except ValueError as e:
        logging.warning(f"日付形式が不正: {e}（全期間表示にフォールバック）")

    try:
        result = load_and_aggregate_pdca_logs(
            log_dir=PDCA_LOG_DIR,
            mode=mode,
            limit=limit,
            from_date=from_dt,
            to_date=to_dt
        )
        logging.info("PDCAログ集計: 成功")
    except Exception as e:
        logging.error(f"PDCAログ集計エラー: {e}", exc_info=True)
        result = {
            "stats": {},
            "chart": {"labels": [], "data": [], "dd_data": []}
        }

    context = {
        "request": request,
        "summary": result.get("stats", {}),
        "chart": result.get("chart", {}),
        "filter": {
            "from": from_date,
            "to": to_date
        },
        "mode": mode,
        "limit": limit,
        "recheck_success": None,
        "recheck_fail": None,
    }
    return templates.TemplateResponse("pdca_summary.html", context)
