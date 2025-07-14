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
    # ここで各種メトリクスを取得（仮データ/本番なら実ロジックで集計）
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
    # 予測データ（例／空リストでもOK。日付はISO8601推奨）
    forecast = [
        {"date": "2025-07-15", "forecast": 150.12, "y_lower": 149.5, "y_upper": 150.9},
        {"date": "2025-07-16", "forecast": 150.38, "y_lower": 149.8, "y_upper": 151.1},
        # ... 必要分だけ
    ]
    # データが無い場合でも forecast = [] で返す
    # forecast = []

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats,
        "forecast": forecast,
    })
