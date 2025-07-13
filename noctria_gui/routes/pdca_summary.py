#!/usr/bin/env python3
# coding: utf-8

"""
📊 /pdca/summary - PDCA再評価の統計サマリ画面
- 再評価結果ログを集計し、改善率や採用数を表示
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from core.path_config import GUI_TEMPLATES_DIR, VERITAS_EVAL_LOG_DIR
from core.pdca_log_parser import load_and_aggregate_pdca_logs

router = APIRouter(prefix="/pdca", tags=["pdca-summary"])
templates = Jinja2Templates(directory=str(GUI_TEMPLATES_DIR))

@router.get("/summary", response_class=HTMLResponse)
async def show_pdca_summary(request: Request):
    # 📥 ログファイルを読み込んで統計を生成
    result = load_and_aggregate_pdca_logs(
        log_dir=VERITAS_EVAL_LOG_DIR,
        mode="strategy",  # または "tag"
        limit=20
    )

    # 📤 統計とチャート情報をテンプレートに渡す
    return templates.TemplateResponse("pdca_summary.html", {
        "request": request,
        "summary": result["stats"],
        "chart": result["chart"]
    })
