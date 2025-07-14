#!/usr/bin/env python3
# coding: utf-8

"""
📊 /dashboard - 中央統治ダッシュボード
- 各種統計と予測分析を統合表示
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

@router.get("/", response_class=HTMLResponse)
async def dashboard_view(request: Request):
    # ここに必要な統計データ集計処理を書く
    # 例として仮データ
    stats = {
        "avg_win_rate": 57.1,
        "avg_drawdown": 13.9,
        "total_strategies": 14,
    }
    # 他に可視化に必要なデータを strategies などで追加する場合はここで渡す
    # 例:
    # strategies = [{ "strategy": ..., "win_rate": ..., ... }]
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats,
        # "strategies": strategies,  # 必要ならここで渡す
    })
