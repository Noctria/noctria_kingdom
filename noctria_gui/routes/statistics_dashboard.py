#!/usr/bin/env python3
# coding: utf-8

"""
📊 /statistics/dashboard - 戦略統計HUDダッシュボード画面
"""

import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR

# サービス層の利用は任意
try:
    from noctria_gui.services.statistics_service import get_strategy_statistics
except ImportError:
    def get_strategy_statistics():
        # 仮ダミーデータ
        return {
            "num_strategies": 10,
            "avg_win_rate": 58.4,
            "avg_drawdown": 11.3,
            "tag_distribution": {
                "Trend": 4,
                "Reversal": 3,
                "Breakout": 3
            }
        }

# ✅ 修正: prefixを追加して /statistics/dashboard に対応
router = APIRouter(prefix="/statistics", tags=["Statistics"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


@router.get("/dashboard", response_class=HTMLResponse)
async def statistics_dashboard(request: Request):
    """
    HUDスタイル統計ダッシュボード画面を表示
    """
    try:
        stats = get_strategy_statistics()
    except Exception as e:
        logging.error(f"Failed to get strategy statistics: {e}", exc_info=True)
        stats = {}

    return templates.TemplateResponse("statistics_dashboard.html", {
        "request": request,
        "stats": stats,
    })
