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
from typing import Optional
from pathlib import Path

from core.path_config import TOOLS_DIR, GUI_TEMPLATES_DIR
from noctria_gui.services import statistics_service

router = APIRouter()
templates = Jinja2Templates(directory=str(GUI_TEMPLATES_DIR))


@router.get("/statistics", response_class=HTMLResponse)
async def show_statistics(
    request: Request,
    strategy: Optional[str] = None,
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sort_key: str = "win_rate",
    descending: bool = True
):
    """
    📈 統計スコアダッシュボードを表示（フィルタ & ソート対応）
    """
    all_logs = statistics_service.load_all_logs()
    filtered = statistics_service.filter_logs(all_logs, strategy, symbol, start_date, end_date)
    sorted_logs = statistics_service.sort_logs(filtered, sort_key, descending)

    return templates.TemplateResponse("statistics_dashboard.html", {
        "request": request,
        "statistics": sorted_logs,
        "filters": {
            "strategy": strategy or "",
            "symbol": symbol or "",
            "start_date": start_date or "",
            "end_date": end_date or ""
        },
        "sort_key": sort_key,
        "descending": descending,
        "strategies": statistics_service.get_available_strategies(all_logs),
        "symbols": statistics_service.get_available_symbols(all_logs),
    })


@router.get("/statistics/export")
async def export_statistics_csv(
    strategy: Optional[str] = None,
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sort_key: str = "win_rate",
    descending: bool = True
):
    """
    📤 統計スコア一覧をCSVでエクスポート（現在のフィルタ・並び順に対応）
    """
    logs = statistics_service.load_all_logs()
    filtered = statistics_service.filter_logs(logs, strategy, symbol, start_date, end_date)
    sorted_logs = statistics_service.sort_logs(filtered, sort_key, descending)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = TOOLS_DIR / f"strategy_statistics_{timestamp}.csv"
    statistics_service.export_logs_to_csv(sorted_logs, output_path)

    return FileResponse(
        output_path,
        filename=output_path.name,
        media_type="text/csv"
    )
