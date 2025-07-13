#!/usr/bin/env python3
# coding: utf-8

"""
📊 /statistics/dashboard - 戦略統計HUDダッシュボード画面
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from services.statistics_service import get_strategy_statistics
from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

@router.get("/statistics/dashboard", response_class=HTMLResponse)
async def statistics_dashboard(request: Request):
    """
    HUDスタイル統計ダッシュボード画面を表示
    """
    # 📊 統計データ取得（例：平均勝率・DD・戦略数・タグ分布など）
    stats = get_strategy_statistics()

    return templates.TemplateResponse("statistics_dashboard.html", {
        "request": request,
        "stats": stats,
    })
