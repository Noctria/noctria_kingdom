#!/usr/bin/env python3
# coding: utf-8

"""
📊 /statistics/dashboard - 戦略統計HUDダッシュボード画面
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR

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
        }

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


@router.get("/dashboard", response_class=HTMLResponse)
async def statistics_dashboard(request: Request):
    """
    HUDスタイル統計ダッシュボード画面を表示
    """
    stats = get_strategy_statistics()

    # ✅ 修正: エラーログに基づき、正しいテンプレートファイル名を指定
    return templates.TemplateResponse("statistics_dashboard.html", {
        "request": request,
        "stats": stats,
    })
