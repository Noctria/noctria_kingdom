#!/usr/bin/env python3
# coding: utf-8

"""
📊 統計ダッシュボード用ルート
- Veritas戦略の統計スコア一覧表示
- フィルタ／ソート／CSVエクスポートに対応
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
from pathlib import Path

from core.path_config import TOOLS_DIR, GUI_TEMPLATES_DIR
from noctria_gui.services import statistics_service

router = APIRouter()
templates = Jinja2Templates(directory=str(GUI_TEMPLATES_DIR))


@router.get("/statistics", response_class=HTMLResponse)
async def show_statistics(request: Request):
    """
    📈 統計スコアダッシュボードを表示
    """
    all_stats = statistics_service.load_all_statistics()
    sorted_stats = statistics_service.filter_statistics(sort_by="win_rate", descending=True)

    return templates.TemplateResponse("statistics_dashboard.html", {
        "request": request,
        "statistics": sorted_stats,
        "strategies": statistics_service.get_available_strategies(all_stats),
        "symbols": statistics_service.get_available_symbols(all_stats),
    })


@router.get("/statistics/export")
async def export_statistics_csv():
    """
    📤 統計スコア一覧をCSVでエクスポート
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = TOOLS_DIR / f"strategy_statistics_{timestamp}.csv"

    stats = statistics_service.load_all_statistics()
    statistics_service.export_statistics_to_csv(stats, output_path)

    return FileResponse(
        output_path,
        filename=output_path.name,
        media_type="text/csv"
    )
