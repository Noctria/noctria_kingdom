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

# 両方のURLで呼び出せるようにデコレーターを2つ付ける
@router.get("/", response_class=HTMLResponse)
@router.get("", response_class=HTMLResponse)
async def dashboard_view(request: Request):
    # 必要な統計データ
    stats = {
        "avg_win_rate": 57.1,
        "avg_drawdown": 13.9,
        "total_strategies": 14,
        "promoted_count": 8,
        "pushed_count": 15,
        "oracle_metrics": {
            "RMSE": 0.0342,
            "MAE": 0.0125,
            "MAPE": 2.81,
        },
    }
    # 予測データ（実装例）
    forecast = [
        {"date": "2025-07-15", "forecast": 150.12, "y_lower": 149.5, "y_upper": 150.9},
        {"date": "2025-07-16", "forecast": 150.38, "y_lower": 149.8, "y_upper": 151.1},
        # ... 必要なら追加
    ]
    # データが無い場合でも空リストで渡す
    # forecast = []

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats,
        "forecast": forecast,
    })
