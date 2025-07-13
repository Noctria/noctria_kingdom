#!/usr/bin/env python3
# coding: utf-8

"""
📊 /pdca/summary - PDCA再評価の統計サマリ画面
- 再評価結果ログを集計し、改善率や採用数を表示
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from core.path_config import GUI_TEMPLATES_DIR
from core.pdca_log_parser import summarize_pdca_logs

router = APIRouter(prefix="/pdca", tags=["pdca-summary"])
templates = Jinja2Templates(directory=str(GUI_TEMPLATES_DIR))

@router.get("/summary", response_class=HTMLResponse)
async def show_pdca_summary(request: Request):
    summary = summarize_pdca_logs()
    return templates.TemplateResponse("pdca_summary.html", {
        "request": request,
        "summary": summary
    })
