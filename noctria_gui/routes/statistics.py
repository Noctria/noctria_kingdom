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
    📈 統計スコアダッシュボードを表示（フィルタ対応）
    """
    # 🔍 クエリパラメータ取得
    strategy = request.query_params.get("strategy", "").strip() or None
    symbol = request.query_params.get("symbol", "").strip() or None
    start_date = request.query_params.get("start_date", "").strip() or None
    end_date = request.query_params.get("end_date", "").strip() or None

    # 📥 全ログ読み込み → フィルタ → ソート
    all_logs = statistics_service.load_all_logs()
    filtered_logs = statistics_service.filter_logs(
        logs=all_logs,
        strategy=strategy,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date
    )
    sorted_logs = statistics_service.sort_logs(
        logs=filtered_logs,
        sort_key="win_rate",
        descending=True
    )

    return templates.TemplateResponse("statistics_dashboard.html", {
        "request": request,
        "statistics": sorted_logs,
        "strategies": statistics_service.get_available_strategies(all_logs),
        "symbols": statistics_service.get_available_symbols(all_logs),
    })


@router.get("/statistics/export")
async def export_statistics_csv():
    """
    📤 統計スコア一覧をCSVでエクスポート
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = TOOLS_DIR / f"strategy_statistics_{timestamp}.csv"

    stats = statistics_service.load_all_logs()
    statistics_service.export_statistics_to_csv(stats, output_path)

    return FileResponse(
        output_path,
        filename=output_path.name,
        media_type="text/csv"
    )
